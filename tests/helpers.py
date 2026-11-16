"""Shared helpers for synthetic dataset tests."""

from __future__ import annotations

from typing import Any

from smart_inspector import InspectionReport


def column(report: InspectionReport, name: str) -> dict[str, Any]:
    """Return one column profile from a report."""
    matches = [item for item in report.to_dict()["columns"] if item["name"] == name]
    if len(matches) != 1:
        raise AssertionError(f"Expected one column named {name!r}, found {len(matches)}.")
    return matches[0]


def findings(
    report: InspectionReport,
    rule_id: str | None = None,
    column_name: str | None = None,
) -> list[dict[str, Any]]:
    """Filter findings by rule and column."""
    rows = report.to_dict()["findings"]
    if rule_id is not None:
        rows = [row for row in rows if row["rule_id"] == rule_id]
    if column_name is not None:
        rows = [row for row in rows if row["column"] == column_name]
    return rows
