"""Command-line interface. It calls the same engine as ``DataInspector``."""

from __future__ import annotations

import argparse
import json
import sys
import traceback
from dataclasses import replace
from pathlib import Path
from typing import Any, Sequence

from smart_inspector.config import ALL_CHECKS, InspectionConfig
from smart_inspector.exceptions import ConfigError, InspectionError
from smart_inspector.inspector import DataInspector


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser used by the CLI."""
    parser = argparse.ArgumentParser(
        prog="python inspector.py",
        description=(
            "Inspect a CSV or JSON dataset and write a readable data-quality report. "
            "The file is not modified."
        ),
        epilog=(
            "examples:\n"
            "  python inspector.py inspect examples/research_data.csv\n"
            "  python inspector.py inspect examples/research_data.json --format json\n"
            "  python inspector.py inspect data.csv --missingness-threshold 0.1 "
            "--disable-check outliers\n"
            "\n"
            "exit codes:\n"
            "  0  inspection completed\n"
            "  1  the file could not be inspected\n"
            "  2  the command or the configuration is invalid\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser(
        "inspect",
        help="Inspect a dataset and write a report",
        description=(
            "Read a UTF-8 CSV (comma-separated, with a header) or a JSON array of "
            "flat objects, then write a Markdown report, a JSON report, or both."
        ),
    )
    inspect_parser.add_argument(
        "path",
        help="Path to a .csv or .json dataset.",
    )
    inspect_parser.add_argument(
        "--output-dir",
        default="reports",
        help="Directory for the report files. Created if needed. Default: reports.",
    )
    inspect_parser.add_argument(
        "--format",
        choices=("markdown", "json", "both"),
        default="both",
        help="Which report files to write. Default: both.",
    )
    inspect_parser.add_argument(
        "--config",
        help=(
            "JSON object of configuration options. Command-line flags override the file. "
            "A custom missing_tokens or enabled_checks list replaces the defaults."
        ),
    )
    inspect_parser.add_argument(
        "--missingness-threshold",
        type=float,
        help="Flag columns whose missing fraction is strictly greater than this value (0 to 1).",
    )
    inspect_parser.add_argument(
        "--outlier-method",
        choices=("iqr",),
        help="Outlier method. Only iqr is implemented.",
    )
    inspect_parser.add_argument(
        "--outlier-multiplier",
        type=float,
        help="IQR fence multiplier. Must be greater than 0. Default: 1.5.",
    )
    inspect_parser.add_argument(
        "--high-cardinality-threshold",
        type=float,
        help=(
            "Flag categorical columns whose distinct-value ratio is at least this value "
            "(greater than 0 and at most 1)."
        ),
    )
    inspect_parser.add_argument(
        "--disable-check",
        action="append",
        default=None,
        dest="disable_checks",
        metavar="CHECK",
        help=(
            "Turn off one quality check. Repeat to turn off more than one. "
            "Choices: missingness, duplicates, mixed_types, outliers, "
            "constant_columns, high_cardinality. "
            "Descriptive statistics are still reported."
        ),
    )
    inspect_parser.add_argument(
        "--debug",
        action="store_true",
        help="Show a traceback if inspection fails.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    try:
        return _inspect(args)
    except ConfigError as exc:
        _report_error(exc, debug=args.debug)
        return 2
    except InspectionError as exc:
        _report_error(exc, debug=args.debug)
        return 1
    except Exception as exc:
        print(f"Unexpected error: {exc}", file=sys.stderr)
        if args.debug:
            traceback.print_exc()
        else:
            print("Re-run with --debug for the full traceback.", file=sys.stderr)
        return 1


def _inspect(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    report = DataInspector(args.path, config=config).inspect()
    written = write_reports(report, args.path, args.output_dir, args.format)
    _print_summary(report, written)
    return 0


def config_from_args(args: argparse.Namespace) -> InspectionConfig:
    """Build a validated config from an optional JSON file and CLI flags."""
    raw: dict[str, Any] = {}
    if args.config:
        raw.update(_load_config_file(Path(args.config)))
    if args.missingness_threshold is not None:
        raw["missingness_threshold"] = args.missingness_threshold
    if args.outlier_method is not None:
        raw["outlier_method"] = args.outlier_method
    if args.outlier_multiplier is not None:
        raw["outlier_multiplier"] = args.outlier_multiplier
    if args.high_cardinality_threshold is not None:
        raw["high_cardinality_threshold"] = args.high_cardinality_threshold
    config = InspectionConfig.from_mapping(raw) if raw else InspectionConfig()
    disabled_names = list(args.disable_checks or [])
    if disabled_names:
        unknown = [name for name in disabled_names if name not in ALL_CHECKS]
        if unknown:
            raise ConfigError(
                "Unknown quality check(s): "
                + ", ".join(unknown)
                + f". Valid checks: {', '.join(ALL_CHECKS)}."
            )
        disabled = set(disabled_names)
        remaining = tuple(check for check in config.enabled_checks if check not in disabled)
        config = replace(config, enabled_checks=remaining)
    return config


def write_reports(report: Any, source: str, output_dir: str, report_format: str) -> list[Path]:
    """Write the selected report files and return their paths."""
    directory = Path(output_dir)
    if directory.exists() and not directory.is_dir():
        raise InspectionError(f"Output path is not a directory: {directory}")
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InspectionError(
            f"Could not create the output directory {directory}: {exc.strerror}."
        ) from exc
    source_name = Path(source).name
    if source_name in {"", ".", ".."}:
        source_name = "dataset"
    # Keep the extension in the report name so dataset.csv and dataset.json
    # do not overwrite each other in the same output directory.
    written: list[Path] = []
    if report_format in {"markdown", "both"}:
        path = directory / f"{source_name}.inspection.md"
        report.to_markdown(path)
        written.append(path)
    if report_format in {"json", "both"}:
        path = directory / f"{source_name}.inspection.json"
        report.to_json(path)
        written.append(path)
    return written


def _load_config_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")
    if not path.is_file():
        raise ConfigError(f"Configuration path is not a file: {path}")
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Configuration file {path} is not valid UTF-8.") from exc
    except OSError as exc:
        raise ConfigError(f"Could not read configuration file {path}: {exc.strerror}.") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Configuration file {path} is not valid JSON: {exc.msg} (line {exc.lineno})."
        ) from exc
    if not isinstance(payload, dict):
        raise ConfigError("Configuration file must contain a JSON object.")
    return payload


def _print_summary(report: Any, written: list[Path]) -> None:
    payload = report.to_dict()
    counts = payload["finding_counts"]
    print("Inspection complete.")
    print(f"Source: {payload['input_file']['path']}")
    print(f"Rows: {payload['overview']['row_count']}")
    print(f"Columns: {payload['overview']['column_count']}")
    print(
        "Duplicate rows (extra copies): "
        f"{payload['duplicates']['extra_duplicate_rows']}"
    )
    print(
        "Findings: "
        f"{counts['total']} "
        f"(error: {counts['error']}, warning: {counts['warning']}, info: {counts['info']})"
    )
    for path in written:
        print(f"Wrote {path}")


def _report_error(exc: BaseException, *, debug: bool) -> None:
    print(f"Error: {exc}", file=sys.stderr)
    if debug:
        traceback.print_exc()
