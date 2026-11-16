"""Command-line interface and the public Python API."""

import json
import subprocess
import sys
from pathlib import Path

from smart_inspector import DataInspector, __version__
from smart_inspector.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_public_api_writes_both_reports(tmp_path: Path) -> None:
    source = tmp_path / "dataset.csv"
    source.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
    report = DataInspector(str(source), config={"missingness_threshold": 0.5}).inspect()
    markdown = report.to_markdown(tmp_path / "report.md")
    payload = json.loads(report.to_json(tmp_path / "report.json"))
    assert "Dataset Overview" in markdown
    assert payload["overview"]["row_count"] == 2
    assert payload["configuration"]["missingness_threshold"] == 0.5
    assert payload["tool"]["version"] == __version__


def test_cli_writes_selected_formats(tmp_path: Path, capsys) -> None:
    source = tmp_path / "dataset.csv"
    source.write_text("a,b\n1,2\n1,2\n", encoding="utf-8")
    output = tmp_path / "out"
    code = main(["inspect", str(source), "--output-dir", str(output), "--format", "both"])
    assert code == 0
    assert (output / "dataset.csv.inspection.md").is_file()
    assert (output / "dataset.csv.inspection.json").is_file()
    captured = capsys.readouterr()
    assert "Inspection complete." in captured.out
    assert "Traceback" not in captured.err

    json_only = tmp_path / "json-only"
    code = main(["inspect", str(source), "--output-dir", str(json_only), "--format", "json"])
    assert code == 0
    assert (json_only / "dataset.csv.inspection.json").is_file()
    assert not (json_only / "dataset.csv.inspection.md").exists()


def test_cli_exit_codes(tmp_path: Path, capsys) -> None:
    missing = main(["inspect", str(tmp_path / "missing.csv")])
    captured = capsys.readouterr()
    assert missing == 1
    assert "File not found" in captured.err
    assert "Traceback" not in captured.err

    source = tmp_path / "data.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    invalid = main(["inspect", str(source), "--missingness-threshold", "2"])
    assert invalid == 2
    assert "missingness_threshold" in capsys.readouterr().err

    text = tmp_path / "notes.txt"
    text.write_text("a,b\n1,2\n", encoding="utf-8")
    assert main(["inspect", str(text)]) == 1


def test_cli_debug_includes_a_traceback(tmp_path: Path, capsys) -> None:
    code = main(["inspect", str(tmp_path / "missing.csv"), "--debug"])
    assert code == 1
    assert "Traceback" in capsys.readouterr().err


def test_cli_disable_check_and_config_override(tmp_path: Path) -> None:
    source = tmp_path / "sparse.csv"
    source.write_text('a\n1\n2\n""\n', encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"missingness_threshold": 0.9}), encoding="utf-8")
    quiet = tmp_path / "quiet"
    code = main(
        [
            "inspect",
            str(source),
            "--config",
            str(config),
            "--output-dir",
            str(quiet),
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads((quiet / "sparse.csv.inspection.json").read_text(encoding="utf-8"))
    assert payload["findings"] == []

    strict = tmp_path / "strict"
    code = main(
        [
            "inspect",
            str(source),
            "--config",
            str(config),
            "--missingness-threshold",
            "0.1",
            "--disable-check",
            "duplicates",
            "--output-dir",
            str(strict),
            "--format",
            "json",
        ]
    )
    assert code == 0
    payload = json.loads((strict / "sparse.csv.inspection.json").read_text(encoding="utf-8"))
    assert [item["rule_id"] for item in payload["findings"]] == ["missingness"]
    assert "duplicates" in payload["configuration"]["disabled_checks"]


def test_cli_rejects_a_bad_config_file(tmp_path: Path, capsys) -> None:
    source = tmp_path / "data.csv"
    source.write_text("a\n1\n", encoding="utf-8")
    config = tmp_path / "bad.json"
    config.write_text("{", encoding="utf-8")
    assert main(["inspect", str(source), "--config", str(config)]) == 2
    assert "not valid JSON" in capsys.readouterr().err


def test_module_and_script_help() -> None:
    script = subprocess.run(
        [sys.executable, str(ROOT / "inspector.py"), "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert script.returncode == 0
    assert "inspect" in script.stdout
    assert "missingness" in script.stdout

    module = subprocess.run(
        [sys.executable, "-m", "smart_inspector", "--help"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert module.returncode == 0
    assert "inspect" in module.stdout

    missing_path = subprocess.run(
        [sys.executable, str(ROOT / "inspector.py"), "inspect"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert missing_path.returncode == 2


def test_shipped_examples_inspect(tmp_path: Path) -> None:
    csv_path = ROOT / "examples" / "research_data.csv"
    json_path = ROOT / "examples" / "research_data.json"
    csv_report = DataInspector(csv_path).inspect()
    rules = {item["rule_id"] for item in csv_report.to_dict()["findings"]}
    assert rules == {
        "missingness",
        "duplicates",
        "mixed_types",
        "outliers",
        "constant_columns",
        "high_cardinality",
    }
    assert csv_report.to_dict()["duplicates"]["extra_duplicate_rows"] == 1

    json_report = DataInspector(json_path).inspect()
    payload = json_report.to_dict()
    retries = next(item for item in payload["columns"] if item["name"] == "retries")
    enrolled = next(item for item in payload["columns"] if item["name"] == "enrolled")
    note = next(item for item in payload["columns"] if item["name"] == "note")
    assert retries["numeric_summary"]["minimum"] == 0
    assert retries["missing_count"] == 0
    assert enrolled["inferred_type"] == "boolean"
    assert enrolled["missing_count"] == 0
    assert note["missing_token_counts"] == {"<absent>": 1, "<null>": 1}
    assert payload["duplicates"]["extra_duplicate_rows"] == 1
    json_report.to_markdown(tmp_path / "example.md")
    json_report.to_json(tmp_path / "example.json")
