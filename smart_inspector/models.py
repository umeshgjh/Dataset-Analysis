"""Public report objects and the JSON-ready column records."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class FileInformation:
    """Where the inspected bytes came from."""

    path: str
    absolute_path: str
    name: str
    format: str
    size_bytes: int
    encoding: str | None


@dataclass
class NumericSummary:
    """Minimum, maximum, and mean for an accepted numeric column.

    ``outlier_assessment`` is filled by the quality engine. ``pending`` should
    never appear in a finished report.
    """

    count: int
    minimum: int | float
    maximum: int | float
    mean: float | None
    mean_note: str | None
    excluded_non_numeric: int
    outlier_assessment: str = "pending"
    outlier_assessment_note: str | None = None


@dataclass
class CategoricalSummary:
    """Mode of an accepted categorical column."""

    unique_count: int
    most_frequent_value: Any
    most_frequent_count: int
    most_frequent_percentage: float
    value_truncated: bool


@dataclass
class ColumnProfile:
    """Inferred type and descriptive facts for one column."""

    name: str
    inferred_type: str
    dominant_type: str
    missing_count: int
    missing_percentage: float
    missing_fraction: float
    missing_token_counts: dict[str, int]
    non_missing_count: int
    unique_non_missing: int
    type_counts: dict[str, int]
    unexpected_count: int
    unexpected_distinct_count: int
    unexpected_values: list[dict[str, Any]]
    classification_note: str
    numeric_summary: NumericSummary | None = None
    categorical_summary: CategoricalSummary | None = None


@dataclass
class DuplicateSummary:
    """Exact-duplicate counts. See ``definition`` for the comparison rule."""

    extra_duplicate_rows: int
    rows_in_duplicate_groups: int
    duplicate_group_count: int
    definition: str


@dataclass
class QualityFinding:
    """One explainable quality result."""

    rule_id: str
    issue_title: str
    severity: str
    scope: str
    column: str | None
    affected_records: int | None
    evidence: dict[str, Any]
    explanation: str
    suggested_action: str


class InspectionReport:
    """The result of one inspection, ready for Markdown and JSON.

    Both writers use the same payload, so the two files cannot disagree about
    a count, a finding, or a threshold.
    """

    def __init__(self, payload: dict[str, Any]) -> None:
        from smart_inspector.reporters.json_report import to_jsonable

        self._payload = to_jsonable(payload)

    def to_dict(self) -> dict[str, Any]:
        """Return a deep copy of the JSON-ready report."""
        copied = copy.deepcopy(self._payload)
        if not isinstance(copied, dict):
            raise TypeError("Inspection report payload must be an object.")
        return copied

    def to_json(self, path: str | Path | None = None) -> str:
        """Serialize the report as JSON and, when ``path`` is set, write it."""
        from smart_inspector.reporters.json_report import dump_report, write_output

        text = dump_report(self._payload)
        if path is not None:
            write_output(path, text)
        return text

    def to_markdown(self, path: str | Path | None = None) -> str:
        """Render the report as Markdown and, when ``path`` is set, write it."""
        from smart_inspector.reporters.json_report import write_output
        from smart_inspector.reporters.markdown import render_markdown

        text = render_markdown(self._payload)
        if path is not None:
            write_output(path, text)
        return text

    def __repr__(self) -> str:
        overview = self._payload.get("overview", {})
        counts = self._payload.get("finding_counts", {})
        return (
            "InspectionReport("
            f"rows={overview.get('row_count')}, "
            f"columns={overview.get('column_count')}, "
            f"findings={counts.get('total')})"
        )
