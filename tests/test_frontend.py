"""The Streamlit client uses the existing engine and drops stale reports."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from smart_inspector import ALL_CHECKS, InspectionConfig
from smart_inspector.exceptions import ConfigError, InspectionError

from app import (
    InspectionOutcome,
    active_downloads,
    apply_config_to_state,
    build_config,
    catalog_frame,
    categorical_table,
    column_names_text,
    column_table,
    config_document,
    configuration_frame,
    STALE_UPLOAD_SECONDS,
    UPLOAD_MARKER_NAME,
    UPLOAD_MARKER_TEXT,
    UPLOAD_LEASE_NAME,
    cleanup_stale_uploads,
    consume_uploads,
    default_export_directory,
    definition_lines,
    discard_upload,
    duplicate_definition,
    duplicate_frame,
    ensure_selection,
    evidence_text,
    file_frame,
    finding_details,
    finding_table,
    format_size,
    load_config_file,
    missing_table,
    new_session_id,
    note_table,
    numeric_table,
    parse_missing_tokens,
    profile_table,
    project_test_command,
    read_form,
    refresh_upload_leases,
    require_dataset_name,
    remember_upload,
    remove_upload,
    run_inspection,
    run_test_suite,
    save_reports,
    selection_from_rows,
    store_outcome,
    store_upload,
    sync_report_to_selection,
    tracked_report_overwrites,
    upload_entries,
    write_upload,
    write_upload_lease,
    _initial_state,
)

ROOT = Path(__file__).resolve().parents[1]


def _config():
    return build_config(
        missingness_threshold=0.2,
        outlier_multiplier=1.5,
        high_cardinality_threshold=0.5,
        enabled_checks=[
            "missingness",
            "duplicates",
            "mixed_types",
            "outliers",
            "constant_columns",
            "high_cardinality",
        ],
    )


def test_assignment_csv_report_and_downloads():
    outcome = run_inspection(
        ROOT / "datasets" / "materials_piezoelectric_properties.csv",
        _config(),
    )
    assert outcome.error is None
    assert outcome.report is not None
    payload = outcome.report.to_dict()
    assert payload["overview"]["row_count"] == 3322
    assert payload["overview"]["column_count"] == 15
    assert payload["finding_counts"]["total"] == 10
    markdown = outcome.report.to_markdown()
    document = json.loads(outcome.report.to_json())
    assert "Column Types" in markdown or "column" in markdown.lower()
    assert document["overview"]["row_count"] == 3322
    assert "Numeric Summaries" in markdown
    assert "Categorical Summaries" in markdown
    assert "Data-Quality Findings" in markdown


def test_flat_json_and_corrupted_csv():
    lab = run_inspection(ROOT / "examples" / "lab_observations.json", _config())
    assert lab.error is None
    assert lab.report is not None
    assert lab.report.to_dict()["overview"]["row_count"] == 8
    assert lab.report.to_dict()["finding_counts"]["total"] == 0

    corrupted = run_inspection(
        ROOT / "examples" / "corrupted_observations.csv",
        _config(),
    )
    assert corrupted.error is None
    assert corrupted.report is not None
    rules = {item["rule_id"] for item in corrupted.report.to_dict()["findings"]}
    assert rules == {
        "missingness",
        "duplicates",
        "mixed_types",
        "outliers",
        "constant_columns",
        "high_cardinality",
    }


def test_nested_json_keeps_the_engine_message_and_no_report():
    outcome = run_inspection(ROOT / "examples" / "nested_document.json", _config())
    assert outcome.report is None
    assert outcome.error is not None
    assert outcome.error.startswith("Unsupported JSON structure:")
    assert "top-level array of flat objects" in outcome.error


def test_empty_and_invalid_inputs(tmp_path: Path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    empty_outcome = run_inspection(empty, _config())
    assert empty_outcome.report is None
    assert empty_outcome.error == "empty.csv is empty."

    header_only = tmp_path / "header.csv"
    header_only.write_text("a,b\n", encoding="utf-8")
    header_outcome = run_inspection(header_only, _config())
    assert header_outcome.report is None
    assert "no data rows" in header_outcome.error

    malformed = tmp_path / "bad.csv"
    malformed.write_text("a,b\n1,2,3\n", encoding="utf-8")
    malformed_outcome = run_inspection(malformed, _config())
    assert malformed_outcome.report is None
    assert malformed_outcome.error.startswith("Malformed CSV")


def test_failure_clears_a_previous_report():
    success = run_inspection(ROOT / "examples" / "lab_observations.json", _config())
    state: dict = {}
    store_outcome(state, success)
    assert state["payload"]["overview"]["row_count"] == 8
    assert state["markdown"].startswith("# Data Inspection Report")
    assert json.loads(state["json_text"])["overview"]["row_count"] == 8
    assert state["download_name"] == "lab_observations.json"

    failure = run_inspection(ROOT / "examples" / "nested_document.json", _config())
    store_outcome(state, failure)
    assert state["payload"] is None
    assert state["markdown"] is None
    assert state["json_text"] is None
    assert state["download_name"] is None
    assert state["error"].startswith("Unsupported JSON structure:")


def test_upload_is_written_outside_the_repository(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.tempfile.NamedTemporaryFile", _tempfile_in(tmp_path))
    path = write_upload("notes.csv", b"a,b\n1,2\n")
    assert path.parent == tmp_path
    assert path.read_bytes() == b"a,b\n1,2\n"
    assert not (ROOT / "datasets" / "notes.csv").exists()
    assert not (ROOT / "notes.csv").exists()


def test_direct_failure_outcome_has_no_report_object():
    outcome = InspectionOutcome(report=None, error="Could not read the file.")
    state = {"payload": {"overview": {"row_count": 1}}, "markdown": "old", "json_text": "{}", "download_name": "old.csv"}
    store_outcome(state, outcome)
    assert state["payload"] is None
    assert state["error"] == "Could not read the file."


class _Handle:
    def __init__(self, path: Path):
        self.path = path
        self._file = path.open("wb")

    def write(self, data: bytes) -> None:
        self._file.write(data)

    def close(self) -> None:
        self._file.close()

    @property
    def name(self) -> str:
        return str(self.path)


def _tempfile_in(directory: Path):
    def _open(*, prefix: str, suffix: str, delete: bool):
        del delete
        return _Handle(directory / f"{prefix}upload{suffix}")

    return _open


class _Upload:
    def __init__(self, name: str, data: bytes, file_id: str = "file-1"):
        self.name = name
        self.size = len(data)
        self.file_id = file_id
        self._data = data

    def getvalue(self) -> bytes:
        return self._data


def test_empty_catalog_does_not_select_a_project_file():
    records, entries = upload_entries([])
    assert records == []
    assert entries == []
    assert ensure_selection(entries, None) is None
    assert ensure_selection(entries, "project:datasets/materials_piezoelectric_properties.csv") is None
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    assert "discover_datasets" not in source
    assert "Refresh datasets" not in source
    assert "Load examples/config.json" not in source
    assert 'type=["csv", "json"]' in source
    assert "materials_piezoelectric_properties" not in source


def test_upload_catalog_detects_format_without_listing_project_files(tmp_path: Path):
    directory = tmp_path / "sdi-upload-z"
    directory.mkdir()
    path = directory / "lab.json"
    path.write_text("[]", encoding="utf-8")
    text_path = directory / "notes.txt"
    text_path.write_text("hello", encoding="utf-8")
    records, entries = upload_entries(
        [
            {"name": "lab.json", "path": str(path)},
            {"name": "notes.txt", "path": str(text_path)},
        ]
    )
    assert [entry.format for entry in entries] == ["json", "unsupported"]
    assert {entry.origin for entry in entries} == {"Upload"}
    frame = catalog_frame(entries)
    assert list(frame.columns) == ["File", "Format", "Size", "Modified", "Location", "Source"]
    assert set(frame["Source"]) == {"Upload"}
    assert set(frame["Format"]) == {"json", "unsupported"}
    assert ensure_selection(entries, None) is None
    assert ensure_selection(entries, entries[1].key) == entries[1].key
    assert ensure_selection(entries, "missing") is None
    assert selection_from_rows(entries, []) is None
    assert selection_from_rows(entries, [1]) == entries[1].key
    assert selection_from_rows(entries, [99]) is None
    assert records[0]["name"] == "lab.json"


def test_format_size_uses_bytes_kilobytes_and_megabytes():
    assert format_size(0) == "0 B"
    assert format_size(512) == "512 B"
    assert format_size(1536) == "1.5 KB"
    assert format_size(2 * 1024 * 1024) == "2.0 MB"


def test_store_upload_keeps_the_original_name_outside_the_repository():
    path = store_upload("../datasets/notes.csv", b"a,b\n1,2\n")
    try:
        assert path.name == "notes.csv"
        assert path.read_bytes() == b"a,b\n1,2\n"
        assert ROOT.resolve() not in path.resolve().parents
        assert not (ROOT / "datasets" / "notes.csv").exists()
    finally:
        discard_upload(path, ROOT)


def test_replacing_an_upload_removes_the_previous_temp_file(tmp_path: Path):
    first_dir = tmp_path / "sdi-upload-a"
    second_dir = tmp_path / "sdi-upload-b"
    first_dir.mkdir()
    second_dir.mkdir()
    first = first_dir / "notes.csv"
    second = second_dir / "notes.csv"
    first.write_bytes(b"old")
    second.write_bytes(b"new")
    records = remember_upload(
        [{"name": "notes.csv", "path": str(first)}],
        "notes.csv",
        second,
        ROOT,
    )
    assert records == [{"name": "notes.csv", "path": str(second.resolve())}]
    assert not first.exists()
    assert second.exists()


def test_discard_refuses_project_files():
    target = ROOT / "examples" / "lab_observations.json"
    before = target.read_bytes()
    try:
        discard_upload(target, ROOT)
    except InspectionError as exc:
        assert "Project files are left unchanged" in str(exc)
    else:
        raise AssertionError("discard_upload removed a project file")
    assert target.read_bytes() == before


def test_remove_upload_deletes_only_the_temporary_file(tmp_path: Path):
    directory = tmp_path / "sdi-upload-c"
    directory.mkdir()
    path = directory / "notes.csv"
    path.write_bytes(b"a,b\n1,2\n")
    key = f"upload:{path.resolve()}"
    kept = remove_upload([{"name": "notes.csv", "path": str(path)}], key, ROOT)
    assert kept == []
    assert not path.exists()


def test_missing_upload_records_are_dropped(tmp_path: Path):
    missing = tmp_path / "gone.csv"
    records, entries = upload_entries([{"name": "gone.csv", "path": str(missing)}])
    assert records == []
    assert entries == []


def test_consume_uploads_stores_one_temporary_copy_per_file():
    first_records, seen, selected, errors = consume_uploads(
        [_Upload("notes.csv", b"a,b\n1,2\n")],
        [],
        [],
        ROOT,
    )
    assert errors == []
    path = Path(first_records[0]["path"])
    try:
        assert path.name == "notes.csv"
        assert ROOT.resolve() not in path.resolve().parents
        assert selected == f"upload:{path.resolve()}"
        again, seen_again, selected_again, errors_again = consume_uploads(
            [_Upload("notes.csv", b"a,b\n1,2\n")],
            first_records,
            seen,
            ROOT,
        )
        assert errors_again == []
        assert again == first_records
        assert seen_again == seen
        assert selected_again is None
    finally:
        discard_upload(path, ROOT)


def test_frontend_accepts_csv_and_json_and_rejects_other_names(tmp_path: Path):
    require_dataset_name("Notes.CSV")
    require_dataset_name("lab.JSON")
    for name in ("notes.txt", "notes", "notes.csv.txt", "../secrets.env"):
        try:
            store_upload(name, b"not a table")
        except InspectionError as exc:
            message = str(exc)
        else:
            raise AssertionError(f"{name} was stored")
        assert "Unsupported file extension" in message
        assert ".csv or .json" in message
    records, seen, selected, errors = consume_uploads(
        [
            _Upload("kept.csv", b"a,b\n1,2\n", file_id="csv"),
            _Upload("notes.txt", b"not a table", file_id="txt"),
            _Upload("kept.json", b"[]", file_id="json"),
        ],
        [],
        [],
        ROOT,
    )
    created = [Path(record["path"]) for record in records]
    try:
        assert [record["name"] for record in records] == ["kept.csv", "kept.json"]
        assert selected == f"upload:{created[-1].resolve()}"
        assert len(errors) == 1
        assert "Unsupported file extension '.txt'" in errors[0]
        assert not any(path.name == "notes.txt" for path in tmp_path.rglob("*"))
        refused = run_inspection(ROOT / "examples" / "nested_document.json", _config())
        assert refused.report is None
        assert refused.error is not None
        assert "Unsupported JSON structure" in refused.error
    finally:
        for path in created:
            discard_upload(path, ROOT)


def _owned_upload(temp_root: Path, name: str, modified_at: float) -> Path:
    directory = temp_root / name
    directory.mkdir()
    (directory / "notes.csv").write_bytes(b"a,b\n1,2\n")
    (directory / UPLOAD_MARKER_NAME).write_bytes(UPLOAD_MARKER_TEXT)
    os.utime(directory / "notes.csv", (modified_at, modified_at))
    os.utime(directory / UPLOAD_MARKER_NAME, (modified_at, modified_at))
    os.utime(directory, (modified_at, modified_at))
    return directory


def test_cleanup_removes_only_stale_owned_upload_directories(tmp_path: Path):
    now = 1_800_000_000.0
    stale = _owned_upload(tmp_path, "sdi-upload-stale", now - STALE_UPLOAD_SECONDS - 60)
    recent = _owned_upload(tmp_path, "sdi-upload-recent", now - 60)
    active = _owned_upload(tmp_path, "sdi-upload-active", now - STALE_UPLOAD_SECONDS - 120)
    foreign = tmp_path / "sdi-upload-foreign"
    foreign.mkdir()
    (foreign / "notes.csv").write_bytes(b"keep")
    os.utime(foreign, (now - STALE_UPLOAD_SECONDS - 60, now - STALE_UPLOAD_SECONDS - 60))
    unrelated = tmp_path / "other-temp"
    unrelated.mkdir()
    (unrelated / "keep.txt").write_text("keep", encoding="utf-8")
    loose = tmp_path / "sdi-upload-loose.csv"
    loose.write_bytes(b"keep")
    nested = _owned_upload(tmp_path, "sdi-upload-nested", now - STALE_UPLOAD_SECONDS - 60)
    (nested / "nested").mkdir()
    link_target = tmp_path / "outside"
    link_target.mkdir()
    (tmp_path / "sdi-upload-link").symlink_to(link_target, target_is_directory=True)
    removed = cleanup_stale_uploads(
        tmp_path,
        now=now,
        active_paths=[active / "notes.csv"],
        project_root=ROOT,
    )
    assert removed == [stale]
    assert not stale.exists()
    assert recent.is_dir()
    assert (active / "notes.csv").is_file()
    assert (foreign / "notes.csv").read_bytes() == b"keep"
    assert (unrelated / "keep.txt").is_file()
    assert loose.is_file()
    assert nested.is_dir()
    assert link_target.is_dir()
    assert (tmp_path / "sdi-upload-link").is_symlink()


def test_cleanup_ignores_a_missing_directory_and_project_owned_paths(tmp_path: Path):
    missing = tmp_path / "does-not-exist"
    assert cleanup_stale_uploads(missing, now=1_800_000_000.0, project_root=ROOT) == []
    now = 1_800_000_000.0
    inside = _owned_upload(tmp_path, "sdi-upload-project", now - STALE_UPLOAD_SECONDS - 60)
    removed = cleanup_stale_uploads(tmp_path, now=now, project_root=tmp_path)
    assert removed == []
    assert inside.is_dir()
    sample = ROOT / "examples" / "lab_observations.json"
    before = sample.read_bytes()
    cleanup_stale_uploads(ROOT, now=now, project_root=ROOT)
    assert sample.read_bytes() == before


def test_cleanup_keeps_another_sessions_live_upload_after_24_hours(tmp_path: Path):
    now = time.time()
    old = now - STALE_UPLOAD_SECONDS - 3600
    session_a = new_session_id()
    session_b = new_session_id()
    live = _owned_upload(tmp_path, "sdi-upload-session-a", old)
    abandoned = _owned_upload(tmp_path, "sdi-upload-session-b", old)
    write_upload_lease(live, session_a)
    write_upload_lease(abandoned, session_b)
    os.utime(abandoned / UPLOAD_LEASE_NAME, (old, old))
    os.utime(live, (old, old))
    os.utime(abandoned, (old, old))
    removed = cleanup_stale_uploads(tmp_path, now=now, project_root=ROOT)
    assert removed == [abandoned]
    assert (live / "notes.csv").is_file()
    assert (live / UPLOAD_LEASE_NAME).read_text(encoding="ascii") == f"{session_a}\n"
    os.utime(live / UPLOAD_LEASE_NAME, (old, old))
    refresh_upload_leases(
        [live / "notes.csv"],
        session_a,
        temp_root=tmp_path,
        project_root=ROOT,
    )
    os.utime(live, (old, old))
    assert cleanup_stale_uploads(tmp_path, now=time.time(), project_root=ROOT) == []
    assert live.is_dir()


def test_cleanup_waits_for_a_lease_refresh_before_deleting(tmp_path: Path):
    import fcntl

    now = time.time()
    old = now - STALE_UPLOAD_SECONDS - 60
    directory = _owned_upload(tmp_path, "sdi-upload-race", old)
    session_a = new_session_id()
    session_b = new_session_id()
    write_upload_lease(directory, session_a)
    os.utime(directory, (old, old))
    os.utime(directory / UPLOAD_LEASE_NAME, (old, old))
    lease = directory / UPLOAD_LEASE_NAME
    fd = os.open(lease, os.O_RDWR | os.O_NOFOLLOW)
    fcntl.flock(fd, fcntl.LOCK_EX)
    result: dict[str, list[Path]] = {}

    def run_cleanup() -> None:
        result["removed"] = cleanup_stale_uploads(tmp_path, now=now, project_root=ROOT)

    worker = threading.Thread(target=run_cleanup)
    worker.start()
    time.sleep(0.2)
    os.ftruncate(fd, 0)
    os.lseek(fd, 0, os.SEEK_SET)
    os.write(fd, f"{session_b}\n".encode("ascii"))
    os.fsync(fd)
    fcntl.flock(fd, fcntl.LOCK_UN)
    os.close(fd)
    worker.join(timeout=5)
    assert not worker.is_alive()
    assert result["removed"] == []
    assert (directory / "notes.csv").is_file()
    assert (directory / UPLOAD_LEASE_NAME).read_text(encoding="ascii") == f"{session_b}\n"


def test_saving_over_tracked_reports_lists_existing_files(tmp_path: Path):
    root = tmp_path / "proj"
    reports = root / "reports"
    reports.mkdir(parents=True)
    markdown = reports / "lab_observations.json.inspection.md"
    document = reports / "lab_observations.json.inspection.json"
    markdown.write_text("sample\n", encoding="utf-8")
    document.write_text("{}\n", encoding="utf-8")
    clashes = tracked_report_overwrites("reports", "lab_observations.json", "both", root)
    assert clashes == [markdown, document]
    assert tracked_report_overwrites("reports", "lab_observations.json", "markdown", root) == [markdown]
    assert tracked_report_overwrites("reports", "new_file.csv", "both", root) == []
    assert tracked_report_overwrites(str(tmp_path / "safe"), "lab_observations.json", "both", root) == []
    assert markdown.read_text(encoding="utf-8") == "sample\n"


def test_save_default_does_not_target_sample_reports():
    destination = Path(default_export_directory())
    assert destination.name == "sdi-exports"
    assert ROOT.resolve() not in destination.resolve().parents
    assert destination.resolve() != (ROOT / "reports").resolve()
    assert _initial_state()["output_dir"] == str(destination)


def test_cleanup_permission_error_leaves_the_directory(tmp_path: Path, monkeypatch):
    now = 1_800_000_000.0
    directory = _owned_upload(tmp_path, "sdi-upload-locked", now - STALE_UPLOAD_SECONDS - 60)

    def refuse(self, *args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "unlink", refuse)
    removed = cleanup_stale_uploads(tmp_path, now=now, project_root=ROOT)
    assert removed == []
    assert directory.is_dir()
    assert (directory / "notes.csv").is_file()


def test_parse_missing_tokens_splits_lines_and_commas():
    assert parse_missing_tokens(" null, none\n\nNA ") == ["null", "none", "NA"]
    assert parse_missing_tokens("   ") == []


def test_form_round_trip_uses_inspection_config():
    state: dict = {}
    apply_config_to_state(state, InspectionConfig())
    state["cfg_missingness"] = 0.1
    state["cfg_min_samples"] = 6
    state["cfg_tokens"] = "missing, absent"
    state["cfg_check_outliers"] = False
    config = read_form(state)
    assert config.missingness_threshold == 0.1
    assert config.outlier_min_samples == 6
    assert config.missing_tokens == ("absent", "missing")
    assert "outliers" not in config.enabled_checks
    document = json.loads(config_document(config))
    assert "disabled_checks" not in document
    assert document["missingness_threshold"] == 0.1


def test_bundled_config_and_invalid_config_use_cli_messages(tmp_path: Path):
    loaded = load_config_file(ROOT / "examples" / "config.json")
    assert loaded.missingness_threshold == 0.2
    assert loaded.outlier_method == "iqr"
    assert loaded.enabled_checks == ALL_CHECKS
    array = tmp_path / "array.json"
    array.write_text("[]", encoding="utf-8")
    try:
        load_config_file(array)
    except ConfigError as exc:
        assert "JSON object" in str(exc)
    else:
        raise AssertionError("an array was accepted as configuration")
    unknown = tmp_path / "unknown.json"
    unknown.write_text('{"score": 1}', encoding="utf-8")
    try:
        load_config_file(unknown)
    except ConfigError as exc:
        assert "Unknown configuration option" in str(exc)
    else:
        raise AssertionError("an unknown option was accepted")


def test_save_reports_matches_the_cli_writer_and_protects_sources(tmp_path: Path):
    outcome = run_inspection(ROOT / "examples" / "lab_observations.json", _config())
    assert outcome.report is not None
    root = tmp_path / "proj"
    (root / "datasets").mkdir(parents=True)
    (root / "examples").mkdir()
    written = save_reports(outcome.report, "lab_observations.json", "out", "both", root)
    assert [path.name for path in written] == [
        "lab_observations.json.inspection.md",
        "lab_observations.json.inspection.json",
    ]
    assert written[0].read_text(encoding="utf-8").startswith("# Data Inspection Report")
    assert json.loads(written[1].read_text(encoding="utf-8"))["overview"]["row_count"] == 8
    markdown_only = save_reports(
        outcome.report,
        "lab_observations.json",
        "markdown-only",
        "markdown",
        root,
    )
    assert [path.suffix for path in markdown_only] == [".md"]
    try:
        save_reports(outcome.report, "lab_observations.json", "datasets", "both", root)
    except InspectionError as exc:
        assert "datasets/" in str(exc)
    else:
        raise AssertionError("reports were written into datasets/")
    assert list((root / "datasets").iterdir()) == []
    try:
        save_reports(outcome.report, "lab_observations.json", " ", "both", root)
    except InspectionError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("an empty output directory was accepted")


def test_debug_detail_is_optional_and_unexpected_errors_are_contained(monkeypatch):
    nested = ROOT / "examples" / "nested_document.json"
    quiet = run_inspection(nested, _config())
    assert quiet.report is None
    assert quiet.detail is None
    assert quiet.error is not None
    assert quiet.error.startswith("Unsupported JSON structure:")
    detailed = run_inspection(nested, _config(), debug=True)
    assert detailed.error == quiet.error
    assert detailed.detail is not None
    assert "Traceback" in detailed.detail

    def boom(*args, **kwargs):
        raise RuntimeError("disk failed")

    monkeypatch.setattr("app.inspect", boom)
    outcome = run_inspection(ROOT / "examples" / "lab_observations.json", _config(), debug=True)
    assert outcome.report is None
    assert outcome.error == "Unexpected error: disk failed"
    assert outcome.detail is not None
    assert "RuntimeError" in outcome.detail


def test_a_later_inspection_replaces_the_visible_result():
    state: dict = {}
    store_outcome(state, run_inspection(ROOT / "examples" / "lab_observations.json", _config()))
    store_outcome(
        state,
        run_inspection(ROOT / "examples" / "corrupted_observations.csv", _config()),
    )
    assert state["payload"]["overview"]["row_count"] == 12
    assert state["download_name"] == "corrupted_observations.csv"
    assert state["report"] is not None


def test_suite_command_is_fixed_and_captured(monkeypatch, tmp_path: Path):
    assert project_test_command()[-3:] == ["-m", "pytest", "-q"]
    seen = {}

    class _Result:
        returncode = 0
        stdout = "100 passed\n"
        stderr = ""

    def fake_run(cmd, cwd, capture_output, text, timeout, check):
        seen["cmd"] = cmd
        seen["cwd"] = cwd
        assert capture_output is True
        assert text is True
        assert check is False
        assert timeout == 180
        return _Result()

    monkeypatch.setattr("app.subprocess.run", fake_run)
    code, output = run_test_suite(tmp_path)
    assert code == 0
    assert seen["cmd"] == project_test_command()
    assert seen["cwd"] == tmp_path
    assert "100 passed" in output


def _assert_views_match_payload(payload: dict) -> None:
    facts = {row.Item: str(row.Value) for row in file_frame(payload).itertuples(index=False)}
    info = payload["input_file"]
    assert facts["File"] == info["name"]
    assert facts["Path"] == info["path"]
    assert facts["Absolute path"] == info["absolute_path"]
    assert facts["Format"] == info["format"]
    assert facts["Size (bytes)"] == str(info["size_bytes"])
    assert facts["Encoding"] == (info["encoding"] or "unspecified")
    assert facts["Inspected at"] == payload["inspected_at"]
    assert facts["Rows"] == str(payload["overview"]["row_count"])
    assert facts["Columns"] == str(payload["overview"]["column_count"])
    assert facts["Tool"] == payload["tool"]["name"]
    assert facts["Tool version"] == payload["tool"]["version"]
    assert facts["Schema"] == payload["schema_version"]
    assert facts["Python"] == payload["runtime"]["python"]
    assert facts["pandas"] == payload["runtime"]["pandas"]
    assert facts["NumPy"] == payload["runtime"]["numpy"]
    assert column_names_text(payload) == ", ".join(payload["overview"]["column_names"])

    columns = column_table(payload)
    assert list(columns["Column"]) == [column["name"] for column in payload["columns"]]
    assert list(columns["Inferred type"]) == [column["inferred_type"] for column in payload["columns"]]
    assert list(columns["Dominant type"]) == [column["dominant_type"] for column in payload["columns"]]
    assert list(columns["Unique"]) == [column["unique_non_missing"] for column in payload["columns"]]
    notes = note_table(payload)
    assert list(notes["Classification"]) == [column["classification_note"] for column in payload["columns"]]
    missing = missing_table(payload)
    assert list(missing["Missing"]) == [column["missing_count"] for column in payload["columns"]]
    assert list(missing["Non-missing"]) == [column["non_missing_count"] for column in payload["columns"]]
    profile = profile_table(payload)
    for column in payload["columns"]:
        row = profile[profile["Column"] == column["name"]].iloc[0]
        assert row["Unexpected"] == column["unexpected_count"]
        assert row["Unexpected distinct"] == column["unexpected_distinct_count"]
        for token in column["missing_token_counts"]:
            assert token in missing[missing["Column"] == column["name"]].iloc[0]["Missing tokens"]
        for kind in column["type_counts"]:
            assert kind in row["Type counts"]
        for sample in column["unexpected_values"]:
            assert str(sample["value"]) in row["Unexpected values"]
            assert str(sample["count"]) in row["Unexpected values"]

    numeric = numeric_table(payload)
    assert list(numeric["Column"]) == [item["column"] for item in payload["numeric_summaries"]]
    for item in payload["numeric_summaries"]:
        row = numeric[numeric["Column"] == item["column"]].iloc[0]
        assert row["Count"] == item["count"]
        assert row["Excluded"] == item["excluded_non_numeric"]
        assert row["Outlier check"] == item["outlier_assessment"]
        assert row["Mean note"] == (item["mean_note"] or "")
        assert row["Outlier note"] == (item["outlier_assessment_note"] or "")
        if item["mean"] is None:
            assert row["Mean"] == "unavailable"

    categorical = categorical_table(payload)
    assert list(categorical["Column"]) == [item["column"] for item in payload["categorical_summaries"]]
    for item in payload["categorical_summaries"]:
        row = categorical[categorical["Column"] == item["column"]].iloc[0]
        assert row["Unique values"] == item["unique_count"]
        assert row["Count"] == item["most_frequent_count"]
        assert str(item["most_frequent_value"]) in row["Most frequent"]
        assert row["Truncated"] == ("yes" if item["value_truncated"] else "no")

    duplicates = payload["duplicates"]
    duplicate_row = duplicate_frame(payload).iloc[0]
    assert duplicate_row["Extra duplicate rows"] == duplicates["extra_duplicate_rows"]
    assert duplicate_row["Rows in duplicate groups"] == duplicates["rows_in_duplicate_groups"]
    assert duplicate_row["Duplicate groups"] == duplicates["duplicate_group_count"]
    assert duplicate_definition(payload) == duplicates["definition"]

    findings = finding_table(payload)
    details = finding_details(payload)
    if payload["findings"]:
        assert list(findings["Severity"]) == [finding["severity"] for finding in payload["findings"]]
        assert list(findings["Scope"]) == [finding["scope"] for finding in payload["findings"]]
        assert list(findings["Finding"]) == [finding["issue_title"] for finding in payload["findings"]]
        assert int((findings["Severity"] == "error").sum()) == payload["finding_counts"]["error"]
        assert int((findings["Severity"] == "warning").sum()) == payload["finding_counts"]["warning"]
        assert int((findings["Severity"] == "info").sum()) == payload["finding_counts"]["info"]
    else:
        assert findings.empty
        assert payload["finding_counts"]["total"] == 0
    assert len(details) == len(payload["findings"])
    for detail, finding in zip(details, payload["findings"], strict=True):
        assert detail["severity"] == finding["severity"]
        assert detail["explanation"] == finding["explanation"]
        assert detail["suggested_action"] == finding["suggested_action"]
        assert detail["scope"] == finding["scope"]
        for key in finding["evidence"]:
            assert key.replace("_", " ") in detail["evidence"]

    shown = configuration_frame(payload["configuration"])
    assert set(shown["Option"]) == set(payload["configuration"])
    rendered = "\n".join(text for _, text in definition_lines(payload))
    for key, value in payload["definitions"].items():
        if isinstance(value, str):
            assert value in rendered
        elif isinstance(value, dict):
            for text in value.values():
                assert text in rendered


def test_views_cover_the_corrupted_lab_and_materials_reports():
    corrupted = run_inspection(ROOT / "examples" / "corrupted_observations.csv", _config())
    lab = run_inspection(ROOT / "examples" / "lab_observations.json", _config())
    materials = run_inspection(
        ROOT / "datasets" / "materials_piezoelectric_properties.csv",
        _config(),
    )
    assert corrupted.report is not None
    assert lab.report is not None
    assert materials.report is not None
    corrupted_payload = corrupted.report.to_dict()
    lab_payload = lab.report.to_dict()
    materials_payload = materials.report.to_dict()
    _assert_views_match_payload(corrupted_payload)
    _assert_views_match_payload(lab_payload)
    _assert_views_match_payload(materials_payload)
    assert corrupted_payload["duplicates"]["extra_duplicate_rows"] == 1
    assert lab_payload["finding_counts"]["total"] == 0
    assert len(column_table(materials_payload)) == 15
    assert list(column_table(materials_payload)["Column"]) == materials_payload["overview"]["column_names"]
    assert "error" not in set(finding_table(materials_payload)["Severity"])
    assert set(finding_table(materials_payload)["Severity"]) == {"info"}


def test_stored_downloads_match_the_report_and_follow_the_selection():
    outcome = run_inspection(ROOT / "examples" / "lab_observations.json", _config())
    assert outcome.report is not None
    state: dict = {"inspected_key": "upload:/tmp/lab.json"}
    store_outcome(state, outcome)
    assert state["markdown"] == outcome.report.to_markdown()
    assert state["json_text"] == outcome.report.to_json()
    assert active_downloads(state, "upload:/tmp/lab.json") == (
        outcome.report.to_markdown(),
        outcome.report.to_json(),
        "lab_observations.json",
    )
    sync_report_to_selection(state, "upload:/tmp/lab.json")
    assert state["markdown"] == outcome.report.to_markdown()
    sync_report_to_selection(state, "upload:/tmp/other.csv")
    assert state["markdown"] is None
    assert state["json_text"] is None
    assert state["download_name"] is None
    assert state["report"] is None
    assert state["inspected_key"] is None
    assert active_downloads(state, "upload:/tmp/other.csv") is None


def test_failed_inspection_cannot_download_the_previous_report(tmp_path: Path):
    state: dict = {"inspected_key": "upload:/tmp/previous.csv"}
    store_outcome(state, run_inspection(ROOT / "examples" / "lab_observations.json", _config()))
    unsupported = tmp_path / "notes.txt"
    unsupported.write_text("not a table", encoding="utf-8")
    failure = run_inspection(unsupported, _config())
    assert failure.report is None
    assert failure.error is not None
    assert "Unsupported file extension" in failure.error
    store_outcome(state, failure)
    state["inspected_key"] = "upload:/tmp/notes.txt"
    assert state["markdown"] is None
    assert state["json_text"] is None
    assert state["download_name"] is None
    assert active_downloads(state, "upload:/tmp/notes.txt") is None
    assert active_downloads(state, "upload:/tmp/previous.csv") is None


def test_views_keep_special_characters_and_missing_cells(tmp_path: Path):
    path = tmp_path / "odd.csv"
    path.write_text('a<b>&,note\n,"x&y <z>"\n1,kept\n', encoding="utf-8")
    outcome = run_inspection(path, _config())
    assert outcome.report is not None
    payload = outcome.report.to_dict()
    assert "a<b>&" in column_names_text(payload)
    assert "a<b>&" in set(column_table(payload)["Column"])
    missing = missing_table(payload)
    assert int(missing[missing["Column"] == "a<b>&"].iloc[0]["Missing"]) == 1
    notes = note_table(payload)
    assert "x&y <z>" in " ".join(notes["Classification"].astype(str)) or "x&y <z>" in " ".join(
        profile_table(payload)["Unexpected values"].astype(str)
    ) or any("x&y <z>" in finding["explanation"] or "x&y <z>" in finding["evidence"] for finding in finding_details(payload)) or "x&y" in outcome.report.to_json()


def test_evidence_text_keeps_every_item():
    text = evidence_text({"rows": list(range(12)), "empty": [], "note": None, "pair": {"left": 1}})
    for number in range(12):
        assert str(number) in text
    assert "…" not in text
    assert "empty: none" in text
    assert "note: none" in text
    assert "left: 1" in text


def test_configuration_view_matches_the_validated_config():
    config = build_config(
        missingness_threshold=0.1,
        outlier_multiplier=1.5,
        high_cardinality_threshold=0.5,
        enabled_checks=[check for check in ALL_CHECKS if check != "outliers"],
    )
    outcome = run_inspection(ROOT / "examples" / "lab_observations.json", config)
    assert outcome.report is not None
    shown = dict(
        zip(
            configuration_frame(outcome.report.to_dict()["configuration"])["Option"],
            configuration_frame(outcome.report.to_dict()["configuration"])["Value"],
            strict=True,
        )
    )
    assert shown["missingness_threshold"] == "0.1"
    assert "outliers" not in shown["enabled_checks"]
    assert "outliers" in shown["disabled_checks"]


def test_app_starts_without_a_dataset_and_downloads_follow_the_upload():
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30)
    app.run()
    assert not app.exception
    page = "\n".join(item.value for item in app.markdown)
    assert "No dataset is loaded." in page
    assert "materials_piezoelectric" not in page
    assert "Refresh datasets" not in page
    assert "Load examples/config.json" not in page
    dataset = next(item for item in app.file_uploader if item.label == "Dataset file")
    assert dataset.allowed_type == [".csv", ".json"]
    assert dataset.accept_multiple_files is True
    config = next(item for item in app.file_uploader if item.label == "Configuration JSON")
    assert config.allowed_type == [".json"]
    lab = (ROOT / "examples" / "lab_observations.json").read_bytes()
    app = dataset.upload("lab_observations.json", lab, "application/json").run()
    assert not app.exception
    page = "\n".join(item.value for item in app.markdown)
    assert "lab_observations.json" in page
    assert "Detected format" in page
    assert "Temporary copy outside the repository" in page
    app = next(item for item in app.button if item.label == "Inspect dataset").click().run()
    assert not app.exception
    labels = [item.label for item in app.download_button]
    assert "Download Markdown" in labels
    assert "Download JSON" in labels
    assert app.session_state["markdown"] == app.session_state["report"].to_markdown()
    assert app.session_state["json_text"] == app.session_state["report"].to_json()
    assert "temperature_c" in app.session_state["markdown"]
    page = "\n".join(item.value for item in app.markdown)
    assert "is ready" not in page
    assert [item.options for item in app.selectbox] == [["lab_observations.json"]]
    notes = b"a,b\n1,2\n3,4\n"
    dataset = next(item for item in app.file_uploader if item.label == "Dataset file")
    app = dataset.upload("notes.csv", notes, "text/csv").run()
    assert not app.exception
    page = "\n".join(item.value for item in app.markdown)
    assert "notes.csv" in page
    assert "Detected format" in page
    assert app.session_state["markdown"] is None
    assert "Download Markdown" not in [item.label for item in app.download_button]
    app = next(item for item in app.button if item.label == "Inspect dataset").click().run()
    assert app.session_state["download_name"] == "notes.csv"
    assert app.session_state["markdown"].startswith("# Data Inspection Report")
    lab_record = next(
        record for record in app.session_state["uploads"] if record["name"] == "lab_observations.json"
    )
    lab_key = f"upload:{Path(lab_record['path']).resolve()}"
    app = app.selectbox[0].set_value(lab_key).run()
    assert app.session_state["selected_key"] == lab_key
    assert app.session_state["markdown"] is None
    assert "Download Markdown" not in [item.label for item in app.download_button]
    nested = (ROOT / "examples" / "nested_document.json").read_bytes()
    dataset = next(item for item in app.file_uploader if item.label == "Dataset file")
    app = dataset.upload("nested_document.json", nested, "application/json").run()
    assert app.session_state["markdown"] is None
    app = next(item for item in app.button if item.label == "Inspect dataset").click().run()
    assert not app.exception
    assert app.session_state["markdown"] is None
    assert app.session_state["json_text"] is None
    assert "Unsupported JSON structure" in (app.session_state["error"] or "")
    assert "Download Markdown" not in [item.label for item in app.download_button]
    dataset = next(item for item in app.file_uploader if item.label == "Dataset file")
    app = dataset.upload("notes.txt", b"not a table", "text/plain").run()
    assert app.exception
    assert "Invalid file extension" in app.exception[0].message
    assert ".txt" in app.exception[0].message
    assert ".csv" in app.exception[0].message
    assert "notes.txt" not in [record["name"] for record in app.session_state["uploads"]]
    assert app.session_state["markdown"] is None
    assert "Download Markdown" not in [item.label for item in app.download_button]
    try:
        for record in list(app.session_state["uploads"]):
            discard_upload(Path(record["path"]), ROOT)
    except Exception:
        pass
