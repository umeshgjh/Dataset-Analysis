"""Streamlit interface for Smart Data Inspector.

The page inspects files the user uploads. It calls ``inspect()`` and writes
reports with ``write_reports``. Parsing, thresholds, and quality checks stay
in ``smart_inspector``.
"""

from __future__ import annotations

import fcntl
import html
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import traceback
from argparse import Namespace
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from smart_inspector import (
    ALL_CHECKS,
    InspectionConfig,
    InspectionError,
    __version__,
    inspect,
)
from smart_inspector.cli import config_from_args, write_reports
from smart_inspector.models import InspectionReport

ROOT = Path(__file__).resolve().parent
PROJECT_FOLDERS = ("datasets", "examples")
DATASET_SUFFIXES = {".csv": "csv", ".json": "json"}
UPLOAD_DIR_PREFIX = "sdi-upload-"
UPLOAD_MARKER_NAME = ".sdi-upload"
UPLOAD_MARKER_TEXT = b"smart-data-inspector\n"
UPLOAD_LEASE_NAME = ".sdi-lease"
STALE_UPLOAD_SECONDS = 24 * 60 * 60
_SESSION_ID = re.compile(r"\A[0-9a-f]{32}\Z")

CHECK_LABELS = {
    "missingness": "Missingness",
    "duplicates": "Duplicates",
    "mixed_types": "Mixed types",
    "outliers": "Outliers",
    "constant_columns": "Constant columns",
    "high_cardinality": "High cardinality",
}

DEFINITION_LABELS = {
    "duplicate_row": "Duplicate row",
    "missing_value": "Missing value",
    "column_type": "Column type",
    "outlier": "Outlier",
    "constant_column": "Constant column",
    "high_cardinality": "High cardinality",
    "severity": "Severity",
    "row_number": "Row number",
    "missingness_comparison": "Missingness comparison",
    "high_cardinality_comparison": "High-cardinality comparison",
    "outlier_comparison": "Outlier comparison",
}

CONFIG_ROWS = (
    "missingness_threshold",
    "outlier_method",
    "outlier_multiplier",
    "outlier_min_samples",
    "high_cardinality_threshold",
    "categorical_max_length",
    "dominance_threshold",
    "enabled_checks",
    "disabled_checks",
    "missing_tokens",
)

REPORT_FORMATS = {
    "both": "Markdown and JSON",
    "markdown": "Markdown",
    "json": "JSON",
}

NO_DATASET_MESSAGE = "Upload a CSV or JSON file before inspecting."

NO_NUMERIC = (
    "No numeric columns were inferred. Integer and float columns appear here "
    "only after a dominant numeric type is accepted. Mixed columns are omitted "
    "so a mean is not reported for an unstable type."
)
NO_CATEGORICAL = (
    "No categorical columns were inferred. Boolean, datetime, numeric, "
    "free-text, mixed, and unknown columns are not given a mode here. "
    "Their unique counts are still listed under Column Types."
)
NO_FINDINGS = (
    "No data-quality findings were raised for the enabled checks. "
    "The descriptive sections above are still the inspection result."
)


@dataclass(frozen=True)
class CatalogEntry:
    """One uploaded file the page can inspect."""

    key: str
    name: str
    location: str
    origin: str
    format: str
    size_bytes: int
    modified: str
    path: Path


@dataclass(frozen=True)
class InspectionOutcome:
    """A finished inspection, or the engine's message and no report."""

    report: InspectionReport | None
    error: str | None
    detail: str | None = None


def detect_format(path: Path) -> str:
    """Identify CSV or JSON from the file name. The engine checks the contents."""
    return DATASET_SUFFIXES.get(path.suffix.lower(), "unsupported")


def format_size(size_bytes: int) -> str:
    """Render a byte count for file metadata."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def format_mtime(timestamp: float) -> str:
    """Render a local modification time."""
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


def upload_entries(records: list[dict]) -> tuple[list[dict], list[CatalogEntry]]:
    """Keep upload records whose temporary files are still present."""
    kept: list[dict] = []
    entries: list[CatalogEntry] = []
    for record in records:
        path = Path(record["path"])
        if not path.is_file():
            continue
        resolved = path.resolve()
        stat = resolved.stat()
        kept.append({"name": record["name"], "path": str(resolved)})
        entries.append(
            CatalogEntry(
                key=f"upload:{resolved}",
                name=record["name"],
                location="temporary upload",
                origin="Upload",
                format=detect_format(Path(record["name"])),
                size_bytes=stat.st_size,
                modified=format_mtime(stat.st_mtime),
                path=resolved,
            )
        )
    return kept, entries


def catalog_frame(entries: list[CatalogEntry]) -> pd.DataFrame:
    """Build the table of files uploaded in this session."""
    return pd.DataFrame(
        [
            {
                "File": entry.name,
                "Format": entry.format,
                "Size": format_size(entry.size_bytes),
                "Modified": entry.modified,
                "Location": entry.location,
                "Source": entry.origin,
            }
            for entry in entries
        ]
    )


def ensure_selection(entries: list[CatalogEntry], current: str | None) -> str | None:
    """Keep a chosen upload. Do not select a file on the user's behalf."""
    keys = {entry.key for entry in entries}
    if current in keys:
        return current
    return None


def selection_from_rows(entries: list[CatalogEntry], rows: list[int]) -> str | None:
    """Map a single browser-row index to a catalog key."""
    if not rows:
        return None
    index = rows[0]
    if index < 0 or index >= len(entries):
        return None
    return entries[index].key


def entry_by_key(entries: list[CatalogEntry], key: str | None) -> CatalogEntry | None:
    for entry in entries:
        if entry.key == key:
            return entry
    return None


def require_dataset_name(name: str) -> None:
    """Refuse an upload whose name is not a CSV or JSON file.

    The extension is detected from the file name. The inspection engine still
    validates the contents of an accepted file.
    """
    suffix = Path(Path(name).name).suffix.lower()
    if suffix in DATASET_SUFFIXES:
        return
    shown = suffix or "(none)"
    raise InspectionError(
        f"Unsupported file extension '{shown}'. "
        "Upload a .csv or .json file. The format is detected from the file name."
    )


def new_session_id() -> str:
    """Return an id that can be stored in an upload lease."""
    return secrets.token_hex(16)


def _valid_session_id(value: str) -> bool:
    return bool(_SESSION_ID.fullmatch(value))


def _lease_text(session_id: str) -> bytes:
    if not _valid_session_id(session_id):
        raise InspectionError("Upload session id is not valid.")
    return f"{session_id}\n".encode("ascii")


def write_upload_lease(directory: Path, session_id: str) -> None:
    """Record or refresh a session lease without following a symlink."""
    payload = _lease_text(session_id)
    lease = directory / UPLOAD_LEASE_NAME
    if lease.is_symlink():
        raise InspectionError("Upload lease is not a regular file.")
    fd = os.open(lease, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, payload)
        os.fsync(fd)
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def store_upload(name: str, data: bytes, session_id: str | None = None) -> Path:
    """Copy an upload to a temporary directory. The repository is not touched."""
    require_dataset_name(name)
    base = Path(name).name
    if base in {"", ".", ".."}:
        base = "upload.csv"
    directory = Path(tempfile.mkdtemp(prefix=UPLOAD_DIR_PREFIX))
    (directory / UPLOAD_MARKER_NAME).write_bytes(UPLOAD_MARKER_TEXT)
    path = directory / base
    path.write_bytes(data)
    owner = session_id if session_id and _valid_session_id(session_id) else new_session_id()
    write_upload_lease(directory, owner)
    return path


def write_upload(name: str, data: bytes) -> Path:
    """Copy bytes to a temporary file. The source dataset is not touched."""
    suffix = Path(name).suffix.lower()
    handle = tempfile.NamedTemporaryFile(
        prefix="sdi-upload-",
        suffix=suffix,
        delete=False,
    )
    try:
        handle.write(data)
    finally:
        handle.close()
    return Path(handle.name)


def discard_upload(path: Path, root: Path) -> None:
    """Delete a temporary upload. Paths inside the project are refused."""
    resolved = path.resolve()
    root_resolved = root.resolve()
    if resolved == root_resolved or root_resolved in resolved.parents:
        raise InspectionError(
            "Project files are left unchanged. Only a temporary upload can be removed."
        )
    resolved.unlink(missing_ok=True)
    parent = resolved.parent
    if not parent.name.startswith(UPLOAD_DIR_PREFIX):
        return
    for name in (UPLOAD_MARKER_NAME, UPLOAD_LEASE_NAME):
        extra = parent / name
        try:
            if extra.is_symlink() or not extra.is_file():
                continue
            extra.unlink()
        except OSError:
            return
    try:
        parent.rmdir()
    except OSError:
        return


def _owned_upload_directory(directory: Path, temp_root: Path, project_root: Path) -> bool:
    """True when a directory is one this application created for an upload."""
    try:
        if directory.is_symlink() or not directory.is_dir():
            return False
        if not directory.name.startswith(UPLOAD_DIR_PREFIX):
            return False
        if directory.name == UPLOAD_DIR_PREFIX:
            return False
        resolved = directory.resolve()
        if resolved.parent != temp_root.resolve():
            return False
        project = project_root.resolve()
        if resolved == project or project in resolved.parents:
            return False
        marker = directory / UPLOAD_MARKER_NAME
        if marker.is_symlink() or not marker.is_file():
            return False
        return marker.read_bytes() == UPLOAD_MARKER_TEXT
    except OSError:
        return False


def _lease_is_current(fd: int, now: float, max_age_seconds: float) -> bool:
    """True when an open lease belongs to a session that has checked in recently."""
    os.lseek(fd, 0, os.SEEK_SET)
    content = os.read(fd, 64)
    if not content.endswith(b"\n"):
        return False
    session_id = content[:-1].decode("ascii", errors="replace")
    if not _valid_session_id(session_id):
        return False
    modified = os.fstat(fd).st_mtime
    return now - modified < max_age_seconds


def _expired_lease_is_locked(directory: Path, now: float, max_age_seconds: float) -> int | None:
    """Lock a stale lease and return its descriptor. ``None`` means it is active.

    A missing lease is not locked. The caller then uses the directory age.
    A symlink is left untouched by returning ``None`` after the caller checks it.
    """
    lease = directory / UPLOAD_LEASE_NAME
    try:
        if lease.is_symlink():
            return None
        if not lease.exists():
            return None
        fd = os.open(lease, os.O_RDWR | os.O_NOFOLLOW)
    except OSError:
        return None
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
    except OSError:
        os.close(fd)
        return None
    try:
        if _lease_is_current(fd, now, max_age_seconds):
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            return None
    except OSError:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
        return None
    return fd


def refresh_upload_leases(
    paths: Iterable[Path],
    session_id: str,
    *,
    temp_root: Path,
    project_root: Path,
) -> None:
    """Heartbeat every upload directory this session still has open."""
    if not _valid_session_id(session_id):
        return
    for path in paths:
        directory = path.parent
        try:
            if _owned_upload_directory(directory, temp_root, project_root):
                write_upload_lease(directory, session_id)
        except OSError:
            continue


def _directory_is_active(directory: Path, active_paths: Iterable[Path]) -> bool:
    try:
        resolved = directory.resolve()
    except OSError:
        return True
    for active in active_paths:
        try:
            candidate = active.resolve()
        except OSError:
            candidate = active
        if candidate == resolved or resolved in candidate.parents:
            return True
    return False


def _remove_owned_directory(directory: Path) -> bool:
    """Remove a flat upload directory. Leave anything with nested entries."""
    try:
        entries = list(directory.iterdir())
    except OSError:
        return False
    files: list[Path] = []
    for entry in entries:
        try:
            if entry.is_symlink() or not entry.is_file():
                return False
        except OSError:
            return False
        files.append(entry)
    for entry in files:
        try:
            entry.unlink()
        except OSError:
            return False
    try:
        directory.rmdir()
    except OSError:
        return False
    return True


def cleanup_stale_uploads(
    temp_root: Path,
    *,
    now: float,
    max_age_seconds: float = STALE_UPLOAD_SECONDS,
    active_paths: Iterable[Path] = (),
    project_root: Path = ROOT,
) -> list[Path]:
    """Delete abandoned upload directories owned by this application.

    A directory is removed only when it is a direct child of ``temp_root``,
    carries the application marker, is outside the project, and has no current
    session lease. A fresh lease keeps the directory at any age. A missing
    lease uses the directory's age, so a directory still being created is kept.
    Symlinks, nested folders, unrelated names, and permission errors are left
    in place. The lease is locked and checked again immediately before deletion.
    """
    removed: list[Path] = []
    try:
        if not temp_root.exists() or not temp_root.is_dir() or temp_root.is_symlink():
            return removed
        children = list(temp_root.iterdir())
    except OSError:
        return removed
    active = list(active_paths)
    for child in children:
        lease_fd: int | None = None
        try:
            if not _owned_upload_directory(child, temp_root, project_root):
                continue
            if _directory_is_active(child, active):
                continue
            lease = child / UPLOAD_LEASE_NAME
            if lease.is_symlink():
                continue
            if lease.exists():
                lease_fd = _expired_lease_is_locked(child, now, max_age_seconds)
                if lease_fd is None:
                    continue
            else:
                age = now - child.stat().st_mtime
                if age < max_age_seconds:
                    continue
            if _remove_owned_directory(child):
                removed.append(child)
        except OSError:
            continue
        finally:
            if lease_fd is not None:
                try:
                    fcntl.flock(lease_fd, fcntl.LOCK_UN)
                except OSError:
                    pass
                os.close(lease_fd)
    return removed


def remember_upload(records: list[dict], name: str, path: Path, root: Path) -> list[dict]:
    """Store an upload, replacing an earlier temporary file of the same name."""
    kept: list[dict] = []
    for record in records:
        if record["name"] == name:
            discard_upload(Path(record["path"]), root)
        else:
            kept.append(record)
    kept.append({"name": name, "path": str(path.resolve())})
    return kept


def remove_upload(records: list[dict], key: str, root: Path) -> list[dict]:
    """Drop one upload record and delete its temporary file."""
    kept: list[dict] = []
    for record in records:
        record_key = f"upload:{Path(record['path']).resolve()}"
        if record_key == key:
            discard_upload(Path(record["path"]), root)
        else:
            kept.append(record)
    return kept


def upload_token(item: object) -> str:
    file_id = getattr(item, "file_id", None)
    if file_id:
        return str(file_id)
    name = getattr(item, "name", "upload")
    size = getattr(item, "size", 0)
    return f"{name}:{size}"


def consume_uploads(
    files,
    records: list[dict],
    seen: list[str],
    root: Path,
    session_id: str | None = None,
):
    """Store newly dropped CSV and JSON files. Other extensions are refused."""
    items = files or []
    if not isinstance(items, (list, tuple)):
        items = [items]
    selected: str | None = None
    seen_tokens = list(seen)
    current = list(records)
    errors: list[str] = []
    for item in items:
        token = upload_token(item)
        if token in seen_tokens:
            continue
        seen_tokens.append(token)
        try:
            path = store_upload(item.name, item.getvalue(), session_id).resolve()
        except InspectionError as exc:
            errors.append(str(exc))
            continue
        current = remember_upload(current, item.name, path, root)
        selected = f"upload:{path}"
    return current, seen_tokens, selected, errors


def parse_missing_tokens(text: str) -> list[str]:
    """Split a token list on commas and newlines."""
    tokens: list[str] = []
    for line in text.replace(",", "\n").splitlines():
        token = line.strip()
        if token:
            tokens.append(token)
    return tokens


def build_config(
    *,
    missingness_threshold: float,
    outlier_multiplier: float,
    high_cardinality_threshold: float,
    enabled_checks: list[str],
    outlier_method: str = "iqr",
    outlier_min_samples: int = 4,
    categorical_max_length: int = 40,
    dominance_threshold: float = 0.8,
    missing_tokens: list[str] | tuple[str, ...] | None = None,
) -> InspectionConfig:
    """Build the same validated config the command line uses."""
    values: dict = {
        "missingness_threshold": missingness_threshold,
        "outlier_method": outlier_method,
        "outlier_multiplier": outlier_multiplier,
        "outlier_min_samples": outlier_min_samples,
        "high_cardinality_threshold": high_cardinality_threshold,
        "categorical_max_length": categorical_max_length,
        "dominance_threshold": dominance_threshold,
        "enabled_checks": tuple(enabled_checks),
    }
    if missing_tokens is not None:
        values["missing_tokens"] = tuple(missing_tokens)
    return InspectionConfig(**values)


def apply_config_to_state(state: dict, config: InspectionConfig) -> None:
    """Copy a validated config into the form fields."""
    data = config.to_dict()
    state["cfg_missingness"] = data["missingness_threshold"]
    state["cfg_multiplier"] = data["outlier_multiplier"]
    state["cfg_min_samples"] = data["outlier_min_samples"]
    state["cfg_cardinality"] = data["high_cardinality_threshold"]
    state["cfg_max_length"] = data["categorical_max_length"]
    state["cfg_dominance"] = data["dominance_threshold"]
    state["cfg_tokens"] = "\n".join(data["missing_tokens"])
    enabled = set(data["enabled_checks"])
    for check in ALL_CHECKS:
        state[f"cfg_check_{check}"] = check in enabled


def read_form(state: dict) -> InspectionConfig:
    """Read the form and validate it with ``InspectionConfig``."""
    enabled = [check for check in ALL_CHECKS if state.get(f"cfg_check_{check}")]
    return build_config(
        missingness_threshold=state["cfg_missingness"],
        outlier_multiplier=state["cfg_multiplier"],
        high_cardinality_threshold=state["cfg_cardinality"],
        enabled_checks=enabled,
        outlier_min_samples=int(state["cfg_min_samples"]),
        categorical_max_length=int(state["cfg_max_length"]),
        dominance_threshold=state["cfg_dominance"],
        missing_tokens=parse_missing_tokens(state.get("cfg_tokens", "")),
    )


def form_summary(config: InspectionConfig) -> str:
    """One line describing the options the next inspection will use."""
    data = config.to_dict()
    return (
        f"Missingness {data['missingness_threshold']:.2f}"
        f" · IQR × {data['outlier_multiplier']:.2f}"
        f" · min samples {data['outlier_min_samples']}"
        f" · high cardinality {data['high_cardinality_threshold']:.2f}"
        f" · label length {data['categorical_max_length']}"
        f" · dominance {data['dominance_threshold']:.2f}"
        f" · {len(data['enabled_checks'])} checks"
        f" · {len(data['missing_tokens'])} missing tokens"
    )


def load_config_file(path: Path) -> InspectionConfig:
    """Load a JSON config with the command-line reader and validator."""
    return config_from_args(
        Namespace(
            config=str(path),
            missingness_threshold=None,
            outlier_method=None,
            outlier_multiplier=None,
            high_cardinality_threshold=None,
            disable_checks=None,
        )
    )


def load_config_bytes(name: str, data: bytes) -> InspectionConfig:
    """Validate uploaded configuration bytes, then delete the temporary file."""
    filename = name if Path(name).suffix.lower() == ".json" else "config.json"
    path = write_upload(filename, data)
    try:
        return load_config_file(path)
    finally:
        path.unlink(missing_ok=True)


def config_document(config: InspectionConfig) -> str:
    """Serialize options that ``InspectionConfig.from_mapping`` accepts."""
    data = config.to_dict()
    data.pop("disabled_checks", None)
    return json.dumps(data, indent=2) + "\n"


def resolve_output_directory(output_dir: str, root: Path) -> Path:
    """Resolve a report directory. Relative paths start at the repository."""
    text = output_dir.strip()
    if text == "":
        raise InspectionError("Output directory is empty.")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def reject_protected_output(directory: Path, root: Path) -> None:
    """Refuse to write reports beside the source datasets."""
    root_resolved = root.resolve()
    for name in PROJECT_FOLDERS:
        protected = (root_resolved / name).resolve()
        if directory == protected or protected in directory.parents:
            raise InspectionError(
                f"Reports are not written into {name}/. Choose a different output directory."
            )


def tracked_report_overwrites(
    output_dir: str,
    source_name: str,
    report_format: str,
    root: Path,
) -> list[Path]:
    """Existing files inside the tracked reports directory that a save would replace."""
    directory = resolve_output_directory(output_dir, root)
    reports = (root.resolve() / "reports").resolve()
    if directory != reports and reports not in directory.parents:
        return []
    source = Path(source_name).name
    if source in {"", ".", ".."}:
        source = "dataset"
    names: list[str] = []
    if report_format in {"markdown", "both"}:
        names.append(f"{source}.inspection.md")
    if report_format in {"json", "both"}:
        names.append(f"{source}.inspection.json")
    return [directory / name for name in names if (directory / name).exists()]


def save_reports(
    report: InspectionReport,
    source_name: str,
    output_dir: str,
    report_format: str,
    root: Path,
) -> list[Path]:
    """Write Markdown and JSON with the command-line report writer."""
    if report_format not in REPORT_FORMATS:
        raise InspectionError("Report format must be markdown, json, or both.")
    directory = resolve_output_directory(output_dir, root)
    reject_protected_output(directory, root)
    return write_reports(report, source_name, str(directory), report_format)


def display_path(path: Path, root: Path) -> str:
    """Prefer a repository-relative path in status text."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(resolved)


def run_inspection(
    path: Path,
    config: InspectionConfig,
    *,
    debug: bool = False,
) -> InspectionOutcome:
    """Inspect one file. An engine error clears any previous report."""
    try:
        report = inspect(path, config=config)
    except InspectionError as exc:
        detail = traceback.format_exc() if debug else None
        return InspectionOutcome(report=None, error=str(exc), detail=detail)
    except Exception as exc:
        detail = traceback.format_exc() if debug else None
        return InspectionOutcome(
            report=None,
            error=f"Unexpected error: {exc}",
            detail=detail,
        )
    return InspectionOutcome(report=report, error=None)


def store_outcome(state: dict, outcome: InspectionOutcome) -> None:
    """Replace the visible result. A failure does not keep the last report."""
    state["error"] = outcome.error
    state["report"] = outcome.report
    if outcome.report is None:
        state["payload"] = None
        state["markdown"] = None
        state["json_text"] = None
        state["download_name"] = None
        return
    payload = outcome.report.to_dict()
    state["payload"] = payload
    state["markdown"] = outcome.report.to_markdown()
    state["json_text"] = outcome.report.to_json()
    state["download_name"] = payload["input_file"]["name"]
    state["error"] = None


def sync_report_to_selection(state: dict, selected_key: str | None) -> None:
    """Drop a stored report when the current file is no longer that report."""
    inspected = state.get("inspected_key")
    if inspected is None or inspected == selected_key:
        return
    store_outcome(state, InspectionOutcome(report=None, error=None))
    state["error_detail"] = None
    state["inspected_key"] = None
    state["save_message"] = None
    state["save_error"] = None


def active_downloads(
    state: dict,
    selected_key: str | None,
) -> tuple[str, str, str] | None:
    """Return Markdown, JSON, and the file name only for the current upload."""
    if selected_key is None or state.get("inspected_key") != selected_key:
        return None
    markdown = state.get("markdown")
    json_text = state.get("json_text")
    name = state.get("download_name")
    if state.get("payload") is None or not markdown or not json_text or not name:
        return None
    return markdown, json_text, name


def form_differs_from_report(state: dict, payload: dict) -> bool:
    """True when the form is not the configuration stored in the report."""
    try:
        current = read_form(state)
    except InspectionError:
        return True
    return current.to_dict() != payload["configuration"]


def project_test_command() -> list[str]:
    """The only test command the interface is allowed to run."""
    return [sys.executable, "-m", "pytest", "-q"]


def run_test_suite(root: Path, timeout: float = 180) -> tuple[int, str]:
    """Run the project test suite. The command cannot be edited from the page."""
    try:
        completed = subprocess.run(
            project_test_command(),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        output = f"{stdout}{stderr}\nThe test suite timed out."
        return 1, output.strip()
    return completed.returncode, f"{completed.stdout}{completed.stderr}".strip()


def _format_scalar(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def _format_number(value: object) -> str:
    if value is None:
        return "unavailable"
    return _format_scalar(value)


def _percent(value: float) -> str:
    return f"{value:.2f}%"


def _mapping_text(mapping: dict) -> str:
    if not mapping:
        return "none"
    return "; ".join(f"{name}: {_format_scalar(count)}" for name, count in mapping.items())


def _unexpected_text(values: list) -> str:
    if not values:
        return "none"
    parts: list[str] = []
    for item in values:
        truncated = "yes" if item.get("truncated") else "no"
        parts.append(
            f"{item.get('value')} (kind {item.get('kind')}, count {item.get('count')}, "
            f"first row {item.get('first_row')}, truncated {truncated})"
        )
    return "; ".join(parts)


def upload_fact_frame(entry: CatalogEntry) -> pd.DataFrame:
    """Metadata shown as soon as a file is uploaded, before inspection."""
    return pd.DataFrame(
        [
            ("File", entry.name),
            ("Detected format", entry.format),
            ("Size", f"{format_size(entry.size_bytes)} ({entry.size_bytes} bytes)"),
            ("Modified", entry.modified),
            ("Storage", "Temporary copy outside the repository"),
        ],
        columns=["Item", "Value"],
    )


def file_frame(payload: dict) -> pd.DataFrame:
    """File, runtime, and shape facts from the inspection payload."""
    info = payload["input_file"]
    runtime = payload["runtime"]
    tool = payload["tool"]
    overview = payload["overview"]
    encoding = info["encoding"] if info["encoding"] else "unspecified"
    rows = [
        ("File", info["name"]),
        ("Path", info["path"]),
        ("Absolute path", info["absolute_path"]),
        ("Format", info["format"]),
        ("Size (bytes)", info["size_bytes"]),
        ("Encoding", encoding),
        ("Inspected at", payload["inspected_at"]),
        ("Rows", overview["row_count"]),
        ("Columns", overview["column_count"]),
        ("Tool", tool["name"]),
        ("Tool version", tool["version"]),
        ("Schema", payload["schema_version"]),
        ("Python", runtime["python"]),
        ("pandas", runtime["pandas"]),
        ("NumPy", runtime["numpy"]),
    ]
    return pd.DataFrame(rows, columns=["Item", "Value"])


def column_names_text(payload: dict) -> str:
    return ", ".join(str(name) for name in payload["overview"]["column_names"])


def column_table(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Column": column["name"],
                "Inferred type": column["inferred_type"],
                "Dominant type": column["dominant_type"],
                "Unique": column["unique_non_missing"],
                "Unexpected": column["unexpected_count"],
                "Unexpected distinct": column["unexpected_distinct_count"],
            }
            for column in payload["columns"]
        ]
    )


def note_table(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"Column": column["name"], "Classification": column["classification_note"]}
            for column in payload["columns"]
        ]
    )


def missing_table(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Column": column["name"],
                "Missing": column["missing_count"],
                "Missing %": _percent(column["missing_percentage"]),
                "Missing fraction": _format_scalar(column["missing_fraction"]),
                "Non-missing": column["non_missing_count"],
                "Missing tokens": _mapping_text(column["missing_token_counts"]),
            }
            for column in payload["columns"]
        ]
    )


def profile_table(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Column": column["name"],
                "Type counts": _mapping_text(column["type_counts"]),
                "Unexpected": column["unexpected_count"],
                "Unexpected distinct": column["unexpected_distinct_count"],
                "Unexpected values": _unexpected_text(column["unexpected_values"]),
            }
            for column in payload["columns"]
        ]
    )


def duplicate_frame(payload: dict) -> pd.DataFrame:
    duplicates = payload["duplicates"]
    return pd.DataFrame(
        [
            {
                "Extra duplicate rows": duplicates["extra_duplicate_rows"],
                "Rows in duplicate groups": duplicates["rows_in_duplicate_groups"],
                "Duplicate groups": duplicates["duplicate_group_count"],
            }
        ]
    )


def duplicate_definition(payload: dict) -> str:
    return str(payload["duplicates"]["definition"])


def numeric_table(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Column": item["column"],
                "Count": item["count"],
                "Minimum": _format_scalar(item["minimum"]),
                "Maximum": _format_scalar(item["maximum"]),
                "Mean": _format_number(item["mean"]),
                "Mean note": item["mean_note"] or "",
                "Excluded": item["excluded_non_numeric"],
                "Outlier check": item["outlier_assessment"],
                "Outlier note": item["outlier_assessment_note"] or "",
            }
            for item in payload["numeric_summaries"]
        ]
    )


def categorical_table(payload: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Column": item["column"],
                "Unique values": item["unique_count"],
                "Most frequent": _format_scalar(item["most_frequent_value"]),
                "Count": item["most_frequent_count"],
                "Share of non-missing": _percent(item["most_frequent_percentage"]),
                "Truncated": "yes" if item["value_truncated"] else "no",
            }
            for item in payload["categorical_summaries"]
        ]
    )


def finding_table(payload: dict) -> pd.DataFrame:
    rows = []
    for finding in payload["findings"]:
        rows.append(
            {
                "Severity": finding["severity"],
                "Check": finding["rule_id"],
                "Scope": finding["scope"],
                "Where": finding["column"] if finding["column"] is not None else "dataset",
                "Affected": (
                    "not applicable"
                    if finding["affected_records"] is None
                    else finding["affected_records"]
                ),
                "Finding": finding["issue_title"],
            }
        )
    return pd.DataFrame(rows)


def evidence_text(evidence: dict) -> str:
    """Render every evidence field the engine returned."""
    if not evidence:
        return "No structured evidence was recorded."
    parts: list[str] = []
    for key, value in evidence.items():
        parts.append(f"{key.replace('_', ' ')}: {_render_evidence_value(value)}")
    return "; ".join(parts)


def finding_details(payload: dict) -> list[dict]:
    """One complete record per finding, using the engine's own wording."""
    details = []
    for finding in payload["findings"]:
        details.append(
            {
                "severity": finding["severity"],
                "issue_title": finding["issue_title"],
                "rule_id": finding["rule_id"],
                "scope": finding["scope"],
                "column": finding["column"] if finding["column"] is not None else "dataset",
                "affected_records": (
                    "not applicable"
                    if finding["affected_records"] is None
                    else finding["affected_records"]
                ),
                "explanation": finding["explanation"],
                "suggested_action": finding["suggested_action"],
                "evidence": evidence_text(finding["evidence"]),
            }
        )
    return details


def definition_lines(payload: dict) -> list[tuple[str, str]]:
    """Every definition string and check description in the payload."""
    definitions = payload.get("definitions") or {}
    lines: list[tuple[str, str]] = []
    for key, label in DEFINITION_LABELS.items():
        value = definitions.get(key)
        if isinstance(value, str):
            lines.append((label, value))
    for name, text in (definitions.get("checks") or {}).items():
        if isinstance(text, str):
            lines.append((str(name), text))
    return lines


def _render_evidence_value(value: object) -> str:
    if value is None:
        return "none"
    if isinstance(value, dict):
        if not value:
            return "none"
        return ", ".join(
            f"{name}: {_render_evidence_value(item)}" for name, item in value.items()
        )
    if isinstance(value, list):
        if not value:
            return "none"
        return "; ".join(_render_evidence_value(item) for item in value)
    return _format_scalar(value)


def configuration_frame(configuration: dict) -> pd.DataFrame:
    keys = [key for key in CONFIG_ROWS if key in configuration]
    keys.extend(key for key in configuration if key not in keys)
    rows = []
    for key in keys:
        value = configuration[key]
        if isinstance(value, list):
            shown = ", ".join(str(item) for item in value) if value else "none"
        else:
            shown = str(value)
        rows.append({"Option": key, "Value": shown})
    return pd.DataFrame(rows)


def _show_table(frame: pd.DataFrame, *, severity: bool = False) -> None:
    """Render a wrapping table. Text stays in the document instead of a canvas cell."""
    if frame.empty:
        return
    headers = "".join(f"<th>{html.escape(str(column))}</th>" for column in frame.columns)
    body: list[str] = []
    for record in frame.to_dict(orient="records"):
        cells: list[str] = []
        for column, value in record.items():
            text = html.escape(str(value))
            if severity and column == "Severity":
                cells.append(f'<td class="{_severity_class(str(value))}">{text}</td>')
            else:
                cells.append(f"<td>{text}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    st.markdown(
        (
            "<div class='table-wrap'><table class='report'>"
            f"<thead><tr>{headers}</tr></thead>"
            f"<tbody>{''.join(body)}</tbody></table></div>"
        ),
        unsafe_allow_html=True,
    )


def _banner(kind: str, message: str) -> None:
    st.markdown(
        f'<div class="banner banner-{kind}">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _facts(frame: pd.DataFrame) -> None:
    rows = []
    for _, row in frame.iterrows():
        rows.append(
            "<div class='fact'>"
            f"<span class='fact-label'>{html.escape(str(row['Item']))}</span>"
            f"<span class='fact-value'>{html.escape(str(row['Value']))}</span>"
            "</div>"
        )
    st.markdown(f"<div class='facts'>{''.join(rows)}</div>", unsafe_allow_html=True)


def _prose(text: str) -> None:
    st.markdown(f"<p class='prose'>{html.escape(text)}</p>", unsafe_allow_html=True)


def _severity_class(severity: str) -> str:
    if severity in {"error", "warning", "info"}:
        return f"sev-{severity}"
    return "sev-unknown"


def inject_css() -> None:
    st.markdown(
        """
        <style>
        html, body, .stApp, [data-testid="stAppViewContainer"] {
            background: #F3F0E8;
            color: #1C2824;
            font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
        }
        .block-container {
            max-width: 1120px;
            padding-top: 2rem;
            padding-bottom: 3rem;
        }
        h1, h2, h3,
        [data-testid="stHeadingWithActionElements"] [data-heading-text] {
            font-family: "Iowan Old Style", Palatino, "Palatino Linotype", Georgia, serif !important;
            font-weight: 500 !important;
            color: #1C2824 !important;
            letter-spacing: 0 !important;
            line-height: 1.3 !important;
        }
        h1, [data-testid="stHeadingWithActionElements"] h1 [data-heading-text] {
            font-size: 1.7rem !important;
        }
        h2, [data-testid="stHeadingWithActionElements"] h2 [data-heading-text] {
            font-size: 1.28rem !important;
        }
        h3, [data-testid="stHeadingWithActionElements"] h3 [data-heading-text] {
            font-size: 1.05rem !important;
        }
        [data-testid="stHeaderActionElements"] { display: none; }
        [data-testid="stExpander"] [data-testid="stIconMaterial"] {
            font-size: 0 !important;
            line-height: 0 !important;
            width: 0.42rem !important;
            height: 0.42rem !important;
            border-right: 1.5px solid #1C2824;
            border-bottom: 1.5px solid #1C2824;
            transform: rotate(-45deg);
            display: inline-block !important;
            margin: 0 0.45rem 0.1rem 0;
            vertical-align: middle;
            overflow: hidden;
            color: transparent;
        }
        details[open] > summary [data-testid="stIconMaterial"] {
            transform: rotate(45deg);
            margin-top: 0.15rem;
        }
        section[data-testid="stSidebar"] {
            background: #24352E;
            border-right: 1px solid #1B2823;
        }
        section[data-testid="stSidebar"] [data-heading-text],
        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
        section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            color: #F6F3EC !important;
        }
        section[data-testid="stSidebar"] button p,
        section[data-testid="stSidebar"] button [data-testid="stMarkdownContainer"] p {
            color: inherit !important;
        }
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
            color: #E4DDD2 !important;
        }
        [data-testid="stSidebarCollapseButton"] [data-testid="stIconMaterial"],
        [data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
            color: #F6F3EC !important;
            opacity: 1 !important;
        }
        section[data-testid="stSidebar"] input,
        section[data-testid="stSidebar"] textarea,
        [data-testid="stMain"] input,
        [data-testid="stMain"] textarea {
            color: #1C2824 !important;
            background: #FFFCF8 !important;
            border: 1px solid #C9C2B4 !important;
            border-radius: 2px !important;
        }
        input::placeholder, textarea::placeholder {
            color: #5C564E !important;
            opacity: 1 !important;
        }
        button:focus-visible, input:focus-visible, textarea:focus-visible,
        [role="combobox"]:focus-visible {
            outline: 2px solid #5E7F68 !important;
            outline-offset: 1px;
        }
        button[data-testid="stBaseButton-primary"] {
            background: #3E624F !important;
            color: #F6F3EC !important;
            border: 1px solid #3E624F !important;
            border-radius: 2px !important;
            box-shadow: none !important;
        }
        button[data-testid="stBaseButton-primary"]:hover {
            background: #4C7360 !important;
            color: #F6F3EC !important;
            border-color: #4C7360 !important;
        }
        button[data-testid="stBaseButton-secondary"],
        .stDownloadButton > button {
            background: #FFFCF8 !important;
            color: #1C2824 !important;
            border: 1px solid #C9C2B4 !important;
            border-radius: 2px !important;
            box-shadow: none !important;
        }
        button[data-testid="stBaseButton-secondary"]:hover,
        .stDownloadButton > button:hover {
            background: #F3F0E8 !important;
            color: #1C2824 !important;
            border-color: #8C867C !important;
        }
        button:disabled, button[disabled] {
            background: #E7E1D6 !important;
            color: #3E4743 !important;
            border-color: #C9C2B4 !important;
        }
        [data-baseweb="popover"],
        [data-baseweb="menu"],
        [role="listbox"] {
            background: #FFFCF8 !important;
            color: #1C2824 !important;
        }
        [role="option"],
        [data-baseweb="menu"] li,
        [data-baseweb="popover"] li {
            background: #FFFCF8 !important;
            color: #1C2824 !important;
        }
        [role="option"][aria-selected="true"],
        [data-baseweb="menu"] li[aria-selected="true"] {
            background: #E4EDE6 !important;
            color: #1C2824 !important;
        }
        [data-testid="stMain"] [data-testid="stCaptionContainer"],
        [data-testid="stMain"] [data-testid="stCaptionContainer"] p {
            color: #3E4A45 !important;
        }
        .table-wrap { overflow-x: auto; margin: 0.35rem 0 0.9rem; }
        table.report {
            width: 100%;
            min-width: 48rem;
            border-collapse: collapse;
            background: #FFFCF8;
            color: #1C2824;
            font-size: 0.92rem;
        }
        table.report th, table.report td {
            border: 1px solid #C9C2B4;
            padding: 0.4rem 0.55rem;
            text-align: left;
            vertical-align: top;
            overflow-wrap: break-word;
            word-break: normal;
            background: #FFFCF8;
            color: #1C2824;
        }
        table.report th {
            background: #EFEBE3;
            color: #1C2824;
            font-weight: 600;
        }
        table.report tbody tr:hover td { background: #F3F0E8; color: #1C2824; }
        table.report td.sev-error { color: #8C4334; font-weight: 600; }
        table.report td.sev-warning { color: #7A5420; font-weight: 600; }
        table.report td.sev-info { color: #1E5C4A; font-weight: 600; }
        table.report tbody tr:hover td.sev-error { color: #8C4334; }
        table.report tbody tr:hover td.sev-warning { color: #7A5420; }
        table.report tbody tr:hover td.sev-info { color: #1E5C4A; }
        [data-testid="stExpander"] details {
            border-radius: 2px !important;
            border: 1px solid #C9C2B4 !important;
            background: #FFFCF8 !important;
            box-shadow: none !important;
        }
        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {
            color: #1C2824 !important;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: #FFFCF8 !important;
            color: #1C2824 !important;
            border: 1px dashed #8C867C !important;
            border-radius: 2px !important;
            height: auto !important;
            min-height: 5.75rem;
        }
        [data-testid="stFileChips"] {
            max-width: 100%;
            max-height: none !important;
            height: auto !important;
        }
        [data-testid="stFileChip"] {
            max-width: 100%;
        }
        [data-testid="stFileUploaderDropzone"] span,
        [data-testid="stFileUploaderDropzone"] small,
        [data-testid="stFileUploaderDropzone"] p,
        [data-testid="stFileUploaderDropzone"] div {
            color: #1C2824 !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
            background: #FFFCF8 !important;
            color: #1C2824 !important;
            border: 1px solid #C9C2B4 !important;
            border-radius: 2px !important;
        }
        [data-testid="stCode"],
        [data-testid="stCode"] pre,
        [data-testid="stCode"] code,
        [data-testid="stCode"] span,
        [data-testid="stMain"] code {
            background: #FFFCF8 !important;
            color: #1C2824 !important;
        }
        [role="tooltip"],
        [data-baseweb="tooltip"],
        [data-testid="stTooltipContent"] {
            background: #24352E !important;
            color: #F6F3EC !important;
        }
        button[data-testid="stExpandSidebarButton"],
        button[data-testid="stSidebarCollapseButton"] {
            background: #24352E !important;
            color: #F6F3EC !important;
            border: 1px solid #5E7F68 !important;
            min-width: 2rem;
            min-height: 2rem;
        }
        .lede, .prose {
            color: #1C2824;
            font-size: 1.02rem;
            line-height: 1.55;
            max-width: 46rem;
            overflow-wrap: anywhere;
        }
        .prose { font-size: 0.98rem; margin: 0.35rem 0 0.7rem; }
        .meta, .ok {
            color: #3E624F;
            font-size: 0.95rem;
            margin: 0.2rem 0 0.8rem;
        }
        .rule {
            border-top: 1px solid #C9C2B4;
            margin: 1.15rem 0 0.95rem;
        }
        .facts { margin: 0.2rem 0 1rem; }
        .fact {
            display: grid;
            grid-template-columns: 12rem minmax(0, 1fr);
            gap: 0.25rem 1rem;
            padding: 0.38rem 0;
            border-bottom: 1px solid #E4DED3;
            color: #1C2824;
        }
        .fact-label { color: #3E4A45; font-weight: 600; }
        .fact-value { color: #1C2824; overflow-wrap: anywhere; }
        .banner {
            background: #FFFCF8;
            border: 1px solid #C9C2B4;
            color: #1C2824;
            padding: 0.8rem 1rem;
            margin: 0.4rem 0 1rem;
            white-space: pre-wrap;
            overflow-wrap: anywhere;
        }
        .banner-error {
            color: #8C4334;
            background: #F8F1ED;
            border-color: #E2C7BE;
            border-left: 3px solid #8C4334;
        }
        .banner-warn {
            color: #7A5420;
            background: #F8F3E8;
            border-color: #E4D3B0;
            border-left: 3px solid #7A5420;
        }
        .banner-hint { border-left: 3px solid #C9C2B4; }
        .finding { margin: 0.8rem 0 1.1rem; }
        .sev {
            font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 0.72rem;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            margin-right: 0.45rem;
        }
        .sev-error { color: #8C4334; }
        .sev-warning { color: #7A5420; }
        .sev-info { color: #1E5C4A; }
        .sev-unknown { color: #1C2824; }
        [data-testid="stElementToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stMainMenu"] { display: none; }
        [data-testid="stToolbar"],
        [data-testid="stHeader"] {
            background: transparent !important;
            box-shadow: none !important;
        }
        @media (max-width: 800px) {
            .block-container { padding-left: 1rem; padding-right: 1rem; }
            .fact { grid-template-columns: 1fr; gap: 0.1rem; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def default_export_directory() -> str:
    """A directory outside the repository for reports saved from the page."""
    return str(Path(tempfile.gettempdir()) / "sdi-exports")


def _maintain_upload_directories() -> None:
    """Refresh this session's leases, then remove abandoned upload directories."""
    session_id = str(st.session_state.get("upload_session_id") or "")
    if not _valid_session_id(session_id):
        session_id = new_session_id()
        st.session_state["upload_session_id"] = session_id
    paths = [
        Path(record["path"])
        for record in st.session_state.get("uploads", [])
        if record.get("path")
    ]
    temp_root = Path(tempfile.gettempdir())
    try:
        refresh_upload_leases(
            paths,
            session_id,
            temp_root=temp_root,
            project_root=ROOT,
        )
        cleanup_stale_uploads(
            temp_root,
            now=time.time(),
            active_paths=paths,
            project_root=ROOT,
        )
    except OSError:
        return


def _initial_state() -> dict:
    state: dict = {
        "output_dir": default_export_directory(),
        "upload_session_id": new_session_id(),
        "report_format": "both",
        "show_debug": False,
        "uploads": [],
        "seen_uploads": [],
        "error": None,
        "payload": None,
        "markdown": None,
        "json_text": None,
        "download_name": None,
        "report": None,
        "error_detail": None,
        "inspected_key": None,
        "save_message": None,
        "save_error": None,
        "save_confirm_files": None,
        "config_message": None,
        "test_result": None,
    }
    apply_config_to_state(state, InspectionConfig())
    return state


def _ensure_state() -> None:
    defaults = _initial_state()
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    pending = st.session_state.pop("pending_config", None)
    if isinstance(pending, InspectionConfig):
        apply_config_to_state(st.session_state, pending)


def _current_entry(entries: list[CatalogEntry]) -> CatalogEntry | None:
    return entry_by_key(entries, st.session_state.get("selected_key"))


def _finish_inspection(entry: CatalogEntry | None, outcome: InspectionOutcome) -> None:
    store_outcome(st.session_state, outcome)
    st.session_state["error_detail"] = outcome.detail
    st.session_state["inspected_key"] = None if entry is None else entry.key
    st.session_state["save_message"] = None
    st.session_state["save_error"] = None
    st.session_state["save_confirm_files"] = None


def _inspect_selected(entry: CatalogEntry | None) -> None:
    if entry is None:
        _finish_inspection(None, InspectionOutcome(report=None, error=NO_DATASET_MESSAGE))
        return
    try:
        require_dataset_name(entry.name)
        require_dataset_name(entry.path.name)
        config = read_form(st.session_state)
    except InspectionError as exc:
        _finish_inspection(entry, InspectionOutcome(report=None, error=str(exc)))
        return
    with st.spinner("Inspecting the dataset…"):
        outcome = run_inspection(
            entry.path,
            config,
            debug=bool(st.session_state.get("show_debug")),
        )
    _finish_inspection(entry, outcome)


def _save_current(*, confirmed: bool = False) -> None:
    report = st.session_state.get("report")
    name = st.session_state.get("download_name")
    if report is None or not name:
        st.session_state["save_error"] = "Inspect a dataset before saving reports."
        st.session_state["save_message"] = None
        return
    output_dir = str(st.session_state.get("output_dir", default_export_directory()))
    report_format = str(st.session_state.get("report_format", "both"))
    try:
        clashes = [] if confirmed else tracked_report_overwrites(output_dir, name, report_format, ROOT)
        if clashes:
            st.session_state["save_error"] = None
            st.session_state["save_message"] = None
            st.session_state["save_confirm_files"] = [
                display_path(path, ROOT) for path in clashes
            ]
            return
        written = save_reports(report, name, output_dir, report_format, ROOT)
    except InspectionError as exc:
        st.session_state["save_confirm_files"] = None
        st.session_state["save_error"] = str(exc)
        st.session_state["save_message"] = None
        return
    st.session_state["save_confirm_files"] = None
    st.session_state["save_error"] = None
    st.session_state["save_message"] = "Wrote " + ", ".join(
        display_path(path, ROOT) for path in written
    )


def _queue_config(config: InspectionConfig, message: str) -> None:
    st.session_state["pending_config"] = config
    st.session_state["config_message"] = message
    st.rerun()


def _render_current_file(entries: list[CatalogEntry], entry: CatalogEntry | None) -> None:
    if entry is None:
        _prose("No dataset is loaded.")
        return
    st.markdown("## Current file")
    _facts(upload_fact_frame(entry))
    if len(entries) > 1:
        st.markdown("### Files in this session")
        _show_table(catalog_frame(entries))
        st.caption("Choose another file in the sidebar. The previous report is cleared when the file changes.")


def _render_configuration() -> None:
    st.markdown("## Configuration")
    st.caption(
        "These are the inspection options. A loaded JSON file fills the fields, "
        "and the fields are validated when the dataset is inspected."
    )
    left, right = st.columns(2)
    with left:
        st.number_input(
            "Missingness threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            format="%.2f",
            key="cfg_missingness",
            help="Flag a column when its missing fraction is strictly greater than this value.",
        )
        st.number_input(
            "Outlier fence multiplier",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            key="cfg_multiplier",
            help="IQR fence multiplier. It must be greater than 0.",
        )
        st.number_input(
            "Outlier minimum samples",
            min_value=1,
            step=1,
            key="cfg_min_samples",
            help="The outlier check needs at least this many finite numbers.",
        )
    with right:
        st.number_input(
            "High-cardinality threshold",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            format="%.2f",
            key="cfg_cardinality",
            help="Flag a categorical column when its distinct-value ratio is at least this value.",
        )
        st.number_input(
            "Categorical label length",
            min_value=1,
            step=1,
            key="cfg_max_length",
            help="Text whose median length is within this limit can be categorical.",
        )
        st.number_input(
            "Dominance threshold",
            min_value=0.5,
            max_value=1.0,
            step=0.01,
            format="%.2f",
            key="cfg_dominance",
            help="Accept a dominant type at this coverage. The value must be greater than 0.5.",
        )
    st.caption("Outlier method is iqr. No other method is implemented.")
    st.markdown("Checks")
    st.caption("Uncheck a check to turn it off. Descriptive summaries are still produced.")
    check_left, check_right = st.columns(2)
    for index, check in enumerate(ALL_CHECKS):
        column = check_left if index % 2 == 0 else check_right
        with column:
            st.checkbox(CHECK_LABELS[check], key=f"cfg_check_{check}")
    st.text_area(
        "Missing tokens",
        key="cfg_tokens",
        height=150,
        help="One token per line, or several separated by commas. This list replaces the defaults.",
    )
    try:
        current = read_form(st.session_state)
    except InspectionError as exc:
        current = None
        _banner("error", str(exc))
    else:
        st.caption(form_summary(current))
        st.download_button(
            "Download configuration",
            data=config_document(current),
            file_name="inspection_config.json",
            mime="application/json",
            key="download_configuration",
        )

    config_upload = st.file_uploader(
        "Configuration JSON",
        type=["json"],
        key="config_upload",
        help="A JSON object of inspection options. The file is validated by the same reader as the command line.",
    )
    apply_column, reset_column = st.columns(2)
    with apply_column:
        apply_clicked = st.button("Apply configuration file", key="apply_config", width="stretch")
    with reset_column:
        reset_clicked = st.button("Reset to defaults", key="reset_config", width="stretch")
    if apply_clicked:
        if config_upload is None:
            st.session_state["config_message"] = "Choose a configuration JSON file."
        else:
            try:
                loaded = load_config_bytes(config_upload.name, config_upload.getvalue())
            except InspectionError as exc:
                st.session_state["config_message"] = str(exc)
            else:
                _queue_config(loaded, f"Loaded {config_upload.name}.")
    if reset_clicked:
        _queue_config(InspectionConfig(), "Restored the default configuration.")
    if st.session_state.get("config_message"):
        st.caption(str(st.session_state["config_message"]))
    if st.button("Inspect dataset", type="primary", key="inspect_main"):
        _inspect_selected(_current_entry(st.session_state.get("_entries", [])))


def _render_status(entry: CatalogEntry | None) -> None:
    error = st.session_state.get("error")
    if error:
        _banner("error", error)
        detail = st.session_state.get("error_detail")
        if detail:
            with st.expander("Error details"):
                st.code(detail, language="text")
        return
    if entry is not None and active_downloads(st.session_state, entry.key) is None:
        _prose(f"{entry.name} is ready. Choose Inspect dataset to read it.")


def _render_results(entry: CatalogEntry | None) -> None:
    downloads = active_downloads(st.session_state, None if entry is None else entry.key)
    if downloads is None:
        return
    payload = st.session_state["payload"]
    markdown, json_text, stem = downloads
    _render_report(payload, markdown, json_text, stem)


def _render_report(payload: dict, markdown: str, json_text: str, stem: str) -> None:
    counts = payload["finding_counts"]
    st.markdown("## Inspection report")
    st.markdown(
        (
            '<p class="ok">'
            f"Inspection complete. {counts['error']} error, "
            f"{counts['warning']} warning, {counts['info']} info."
            "</p>"
        ),
        unsafe_allow_html=True,
    )
    if form_differs_from_report(st.session_state, payload):
        _banner(
            "warn",
            "The form has changed since this inspection. "
            "Inspect the dataset again to apply it. "
            "The download still uses the configuration recorded in this report.",
        )
    download_row = st.columns(2)
    with download_row[0]:
        st.download_button(
            "Download Markdown",
            data=markdown,
            file_name=f"{stem}.inspection.md",
            mime="text/markdown",
            width="stretch",
            key=f"md-{stem}-{payload['inspected_at']}",
        )
    with download_row[1]:
        st.download_button(
            "Download JSON",
            data=json_text,
            file_name=f"{stem}.inspection.json",
            mime="application/json",
            width="stretch",
            key=f"json-{stem}-{payload['inspected_at']}",
        )
    save_left, save_right = st.columns([2, 1])
    with save_left:
        st.text_input(
            "Output directory",
            key="output_dir",
            help=(
                "Absolute path, or a path relative to the repository. "
                "The default is a temporary export directory, so a normal save "
                "does not replace the samples in reports/. "
                "Saving into reports/ asks for confirmation before an existing file is replaced."
            ),
        )
    with save_right:
        st.radio(
            "Report files",
            list(REPORT_FORMATS),
            format_func=lambda value: REPORT_FORMATS[value],
            key="report_format",
            horizontal=True,
        )
    if st.button("Save reports", key="save_reports"):
        _save_current()
    pending = st.session_state.get("save_confirm_files") or []
    if pending:
        _banner(
            "warn",
            "Saving would replace files in reports/: "
            + ", ".join(str(path) for path in pending)
            + ". Choose Replace files in reports/ to continue.",
        )
        if st.button("Replace files in reports/", key="confirm_overwrite"):
            _save_current(confirmed=True)
    if st.session_state.get("save_error"):
        _banner("error", str(st.session_state["save_error"]))
    if st.session_state.get("save_message"):
        st.markdown(
            f'<p class="ok">{html.escape(str(st.session_state["save_message"]))}</p>',
            unsafe_allow_html=True,
        )

    st.markdown("## File")
    _facts(file_frame(payload))
    st.markdown("## Dataset")
    _prose(
        f"The table has {payload['overview']['row_count']} rows and "
        f"{payload['overview']['column_count']} columns."
    )
    _prose("Column names, in file order: " + column_names_text(payload))

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Column types")
    _prose(
        "Types are inferred from the non-missing values. "
        "dominant_type is the kind that covers the most values. "
        "inferred_type is categorical for short labels, string for free text, "
        "mixed when no kind is stable, and unknown when every value is missing."
    )
    _show_table(column_table(payload))
    st.markdown("### Classification notes")
    for row in note_table(payload).itertuples(index=False):
        _prose(f"{row.Column}: {row.Classification}")

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Missing values")
    _prose(payload["definitions"]["missing_value"])
    _show_table(missing_table(payload))

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Type counts and unexpected values")
    for row in profile_table(payload).to_dict(orient="records"):
        _prose(
            f"{row['Column']}: type counts {row['Type counts']}; "
            f"unexpected {row['Unexpected']}; "
            f"unexpected distinct {row['Unexpected distinct']}; "
            f"unexpected values {row['Unexpected values']}."
        )

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Duplicate rows")
    _prose(duplicate_definition(payload))
    _show_table(duplicate_frame(payload))

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Numeric summaries")
    if payload["numeric_summaries"]:
        _prose(
            "Minimum, maximum, and mean use only values compatible with the accepted "
            "numeric type. Excluded cells are non-numeric values left out of those statistics. "
            "The table shows numbers to 6 decimal places; the JSON report keeps full precision."
        )
        _show_table(numeric_table(payload))
        for item in payload["numeric_summaries"]:
            if item.get("mean_note"):
                _prose(f"{item['column']}: {item['mean_note']}")
            if item.get("outlier_assessment_note"):
                _prose(f"{item['column']}: {item['outlier_assessment_note']}")
    else:
        _prose(NO_NUMERIC)

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Categorical summaries")
    if payload["categorical_summaries"]:
        _prose(
            "The most frequent value is the first non-missing value that reaches the "
            "highest count. Ties keep the value that appears earliest in the file. "
            "The share is the count divided by non-missing values."
        )
        _show_table(categorical_table(payload))
    else:
        _prose(NO_CATEGORICAL)

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Findings")
    _prose(
        f"{counts['total']} finding(s): {counts['error']} error, "
        f"{counts['warning']} warning, {counts['info']} info."
    )
    findings = finding_details(payload)
    if findings:
        _show_table(finding_table(payload), severity=True)
        for index, finding in enumerate(findings, start=1):
            severity = html.escape(str(finding["severity"]))
            title = html.escape(str(finding["issue_title"]))
            st.markdown(
                (
                    f'<h3 class="finding"><span class="sev {_severity_class(finding["severity"])}">'
                    f"{severity}</span> {index}. {title}</h3>"
                ),
                unsafe_allow_html=True,
            )
            _prose(f"Rule: {finding['rule_id']}")
            _prose(f"Scope: {finding['scope']}")
            _prose(f"Affected column or dataset: {finding['column']}")
            _prose(f"Affected records: {finding['affected_records']}")
            _prose(f"Evidence: {finding['evidence']}")
            _prose(finding["explanation"])
            _prose(f"Suggested action: {finding['suggested_action']}")
    else:
        _prose(NO_FINDINGS)

    st.markdown('<div class="rule"></div>', unsafe_allow_html=True)
    st.markdown("## Configuration used")
    _prose("These are the settings that produced this report.")
    _show_table(configuration_frame(payload["configuration"]))

    st.markdown("## Definitions")
    for label, text in definition_lines(payload):
        _prose(f"{label}. {text}")

    with st.expander("Markdown report"):
        st.code(markdown, language="markdown")
    with st.expander("JSON report"):
        st.code(json_text, language="json")


def _render_developer() -> None:
    with st.expander("Developer"):
        st.markdown(
            "Run the project test suite. The command is `python -m pytest -q` "
            "and cannot be changed here."
        )
        st.markdown(
            "Creating the environment, installing dependencies, and git "
            "remain terminal commands."
        )
        if st.button("Run tests", key="run_tests"):
            with st.spinner("Running the test suite…"):
                code, output = run_test_suite(ROOT)
            st.session_state["test_result"] = (code, output)
        result = st.session_state.get("test_result")
        if result:
            code, output = result
            st.caption(f"Exit code {code}")
            st.code(output or "(no output)")


def _render_sidebar(entries: list[CatalogEntry]) -> None:
    st.markdown("## Dataset")
    if not entries:
        st.caption("Uploaded files appear here.")
        return
    labels = {item.key: item.name for item in entries}
    choice = st.session_state.get("selected_key")
    if choice not in labels:
        st.session_state["selected_key"] = None
        st.selectbox(
            "Current dataset",
            options=list(labels),
            format_func=lambda key: labels[key],
            index=None,
            placeholder="Choose an uploaded dataset",
            key="selected_key",
        )
    else:
        st.selectbox(
            "Current dataset",
            options=list(labels),
            format_func=lambda key: labels[key],
            key="selected_key",
        )
    current = _current_entry(entries)
    if current is None:
        st.caption("Choose a file to inspect.")
        return
    st.caption(f"{current.format} · {format_size(current.size_bytes)} · {current.modified}")
    st.caption("Temporary copy. The uploaded file is not modified.")
    if st.button("Remove this file", key="remove_upload", width="stretch"):
        st.session_state["uploads"] = remove_upload(
            list(st.session_state.get("uploads", [])),
            current.key,
            ROOT,
        )
        st.session_state["selected_key"] = None
        st.rerun()


def _prepare_catalog(uploads) -> list[CatalogEntry]:
    if uploads:
        records, seen, selected, errors = consume_uploads(
            uploads,
            list(st.session_state.get("uploads", [])),
            list(st.session_state.get("seen_uploads", [])),
            ROOT,
            str(st.session_state.get("upload_session_id") or "") or None,
        )
        st.session_state["uploads"] = records
        st.session_state["seen_uploads"] = seen
        if errors:
            st.session_state["upload_error"] = errors[-1]
        elif selected is not None:
            st.session_state["upload_error"] = None
        if selected is not None:
            st.session_state["selected_key"] = selected
    elif st.session_state.get("seen_uploads"):
        st.session_state["seen_uploads"] = []
    records, entries = upload_entries(list(st.session_state.get("uploads", [])))
    st.session_state["uploads"] = records
    chosen = ensure_selection(entries, st.session_state.get("selected_key"))
    st.session_state["selected_key"] = chosen
    sync_report_to_selection(st.session_state, chosen)
    st.session_state["_entries"] = entries
    return entries


def main() -> None:
    st.set_page_config(
        page_title="Smart Data Inspector",
        layout="wide",
        initial_sidebar_state="auto",
    )
    inject_css()
    _ensure_state()
    _maintain_upload_directories()
    st.markdown("# Smart Data Inspector")
    st.markdown(
        '<p class="lede">Upload a CSV or JSON file. The format is detected from the file name. '
        "The file is not modified.</p>",
        unsafe_allow_html=True,
    )
    dataset_upload = st.file_uploader(
        "Dataset file",
        type=["csv", "json"],
        accept_multiple_files=True,
        key="dataset_upload",
        help="Browse or drop a .csv or .json file. The format is detected from the file name.",
    )
    entries = _prepare_catalog(dataset_upload)
    if st.session_state.get("upload_error"):
        _banner("error", str(st.session_state["upload_error"]))
    with st.sidebar:
        st.caption(f"Version {__version__}")
        _render_sidebar(entries)
        st.checkbox(
            "Include error details",
            key="show_debug",
            help="Show the Python traceback when an inspection fails. This is the --debug choice.",
        )
        if st.button("Inspect dataset", type="primary", key="inspect_sidebar", width="stretch"):
            _inspect_selected(_current_entry(entries))
    entry = _current_entry(entries)
    _render_current_file(entries, entry)
    _render_configuration()
    _render_status(entry)
    _render_results(entry)
    _render_developer()


if __name__ == "__main__":
    main()
