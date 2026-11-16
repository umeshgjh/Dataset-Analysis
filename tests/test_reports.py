"""Markdown and JSON render the same inspection."""

import json
import re

from smart_inspector import __version__
from tests.helpers import findings


REQUIRED_KEYS = {
    "schema_version",
    "tool",
    "runtime",
    "inspected_at",
    "input_file",
    "overview",
    "columns",
    "duplicates",
    "numeric_summaries",
    "categorical_summaries",
    "findings",
    "finding_counts",
    "configuration",
    "definitions",
}

HEADINGS = [
    "# Data Inspection Report",
    "## Input File",
    "## Dataset Overview",
    "## Column Types",
    "## Missing-Value Analysis",
    "## Duplicate Rows",
    "## Numeric Summaries",
    "## Categorical Summaries",
    "## Data-Quality Findings",
    "## Inspection Configuration",
    "## Definitions",
]


def test_json_and_markdown_share_one_result(inspect_file, tmp_path) -> None:
    report = inspect_file(
        "sample.csv",
        "name,score,note\n"
        "a,1,red\n"
        "a,1,red\n"
        "b,100,blue\n"
        "c,,blue\n"
        "d,3,blue\n",
    )
    payload = report.to_dict()
    json_text = report.to_json(tmp_path / "report.json")
    markdown = report.to_markdown(tmp_path / "report.md")
    loaded = json.loads(json_text)
    assert loaded == payload
    assert loaded == report.to_dict()
    assert REQUIRED_KEYS <= loaded.keys()
    assert loaded["tool"]["version"] == __version__
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", loaded["inspected_at"])
    assert "quality_score" not in loaded
    assert loaded["duplicates"]["definition"] == loaded["definitions"]["duplicate_row"]
    for heading in HEADINGS:
        assert heading in markdown
    assert str(loaded["overview"]["row_count"]) in markdown
    assert str(loaded["duplicates"]["extra_duplicate_rows"]) in markdown
    for finding in loaded["findings"]:
        assert finding["issue_title"] in markdown
        assert finding["explanation"] in markdown
        assert finding["suggested_action"] in markdown
        for key in (
            "rule_id",
            "issue_title",
            "severity",
            "column",
            "affected_records",
            "evidence",
            "explanation",
            "suggested_action",
        ):
            assert key in finding
    assert ": NaN" not in json_text
    assert ": Infinity" not in json_text
    assert (tmp_path / "report.json").read_text(encoding="utf-8") == json_text
    assert (tmp_path / "report.md").read_text(encoding="utf-8") == markdown


def test_repeated_inspection_is_deterministic_except_for_the_timestamp(inspect_file) -> None:
    text = "a,b\n1,2\n1,2\n3,\n"
    first = inspect_file("one.csv", text).to_dict()
    second = inspect_file("two.csv", text).to_dict()
    first.pop("inspected_at")
    second.pop("inspected_at")
    first["input_file"].pop("path")
    second["input_file"].pop("path")
    first["input_file"].pop("absolute_path")
    second["input_file"].pop("absolute_path")
    first["input_file"].pop("name")
    second["input_file"].pop("name")
    first["input_file"].pop("size_bytes")
    second["input_file"].pop("size_bytes")
    assert first == second


def test_empty_summary_sections_are_still_present(inspect_file) -> None:
    report = inspect_file("text.csv", "comment\n" + ("A long free-text comment about the visit.\n" * 3))
    markdown = report.to_markdown()
    assert "No numeric columns were inferred" in markdown
    assert "No categorical columns were inferred" in markdown
    assert report.to_dict()["numeric_summaries"] == []
    assert report.to_dict()["categorical_summaries"] == []


def test_finding_order_follows_rules_then_columns(inspect_file) -> None:
    report = inspect_file(
        "order.csv",
        "later,earlier,const\n"
        "1,,x\n"
        "2,,x\n"
        "3,y,x\n"
        "4,,x\n"
        "100,,x\n",
    )
    rule_ids = [item["rule_id"] for item in report.to_dict()["findings"]]
    assert "missingness" in rule_ids
    assert rule_ids.index("missingness") < rule_ids.index("outliers")
    missing_columns = [item["column"] for item in findings(report, "missingness")]
    assert missing_columns == ["earlier"] or missing_columns[0] == "earlier"
