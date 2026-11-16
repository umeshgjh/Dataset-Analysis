"""Report assembly. The CLI and the Python API both call this module."""

from __future__ import annotations

import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import pandas as pd

from smart_inspector.config import InspectionConfig
from smart_inspector.definitions import (
    CHECK_CATALOG,
    CONSTANT_DEFINITION,
    DUPLICATE_DEFINITION,
    HIGH_CARDINALITY_COMPARISON,
    HIGH_CARDINALITY_DEFINITION,
    MISSING_DEFINITION,
    MISSINGNESS_COMPARISON,
    OUTLIER_COMPARISON,
    OUTLIER_DEFINITION,
    ROW_NUMBER_DEFINITION,
    SEVERITY_DEFINITION,
    TYPE_DEFINITION,
)
from smart_inspector.exceptions import ConfigError
from smart_inspector.loader import load_dataset
from smart_inspector.models import (
    CategoricalSummary,
    ColumnProfile,
    DuplicateSummary,
    InspectionReport,
    NumericSummary,
    QualityFinding,
)
from smart_inspector.profiler import profile_dataset
from smart_inspector.quality import evaluate_quality
from smart_inspector.version import SCHEMA_VERSION, TOOL_NAME, __version__


class DataInspector:
    """Inspect one CSV or JSON dataset.

    The file is read when :meth:`inspect` is called, not when the inspector is
    constructed. Configuration is validated immediately.

    Example:
        >>> inspector = DataInspector("dataset.csv")
        >>> report = inspector.inspect()
        >>> report.to_markdown("report.md")
        >>> report.to_json("report.json")
    """

    def __init__(
        self,
        source: str | Path,
        config: InspectionConfig | Mapping[str, Any] | None = None,
    ) -> None:
        self.source = source
        self.config = resolve_config(config)

    def inspect(self) -> InspectionReport:
        """Read the dataset and return a Markdown/JSON report object.

        Calling this method does not write a file and does not modify the source.
        A second call reads the file again. Results are deterministic for the
        same bytes and configuration, except for ``inspected_at``.
        """
        loaded = load_dataset(self.source)
        profiled = profile_dataset(loaded.frame, self.config)
        findings = evaluate_quality(profiled, self.config)
        payload = _payload(
            file_info=loaded.file_info,
            columns=[column.profile for column in profiled.columns],
            duplicates=profiled.duplicates,
            findings=findings,
            config=self.config,
            row_count=profiled.row_count,
            column_names=profiled.column_names,
        )
        return InspectionReport(payload)


def inspect(
    source: str | Path,
    config: InspectionConfig | Mapping[str, Any] | None = None,
) -> InspectionReport:
    """Inspect ``source`` with the shared inspection engine."""
    return DataInspector(source, config=config).inspect()


def resolve_config(
    config: InspectionConfig | Mapping[str, Any] | None,
) -> InspectionConfig:
    """Validate a config object, a mapping, or the defaults."""
    if config is None:
        return InspectionConfig()
    if isinstance(config, InspectionConfig):
        return config
    if isinstance(config, Mapping):
        return InspectionConfig.from_mapping(config)
    raise ConfigError(
        "Configuration must be an InspectionConfig or a mapping of option names to values. "
        f"Got {type(config).__name__}."
    )


def _payload(
    *,
    file_info: Any,
    columns: list[ColumnProfile],
    duplicates: DuplicateSummary,
    findings: list[QualityFinding],
    config: InspectionConfig,
    row_count: int,
    column_names: list[str],
) -> dict[str, Any]:
    counts = {"error": 0, "warning": 0, "info": 0}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1
    total = counts["error"] + counts["warning"] + counts["info"]
    inspected_at = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": TOOL_NAME, "version": __version__},
        "runtime": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "inspected_at": inspected_at,
        "input_file": {
            "path": file_info.path,
            "absolute_path": file_info.absolute_path,
            "name": file_info.name,
            "format": file_info.format,
            "size_bytes": file_info.size_bytes,
            "encoding": file_info.encoding,
        },
        "overview": {
            "row_count": row_count,
            "column_count": len(column_names),
            "column_names": list(column_names),
        },
        "columns": [_column_dict(column) for column in columns],
        "duplicates": {
            "extra_duplicate_rows": duplicates.extra_duplicate_rows,
            "rows_in_duplicate_groups": duplicates.rows_in_duplicate_groups,
            "duplicate_group_count": duplicates.duplicate_group_count,
            "definition": duplicates.definition,
        },
        "numeric_summaries": [
            {"column": column.name, **_numeric_dict(column.numeric_summary)}
            for column in columns
            if column.numeric_summary is not None
        ],
        "categorical_summaries": [
            {"column": column.name, **_categorical_dict(column.categorical_summary)}
            for column in columns
            if column.categorical_summary is not None
        ],
        "findings": [_finding_dict(finding) for finding in findings],
        "finding_counts": {
            "error": counts["error"],
            "warning": counts["warning"],
            "info": counts["info"],
            "total": total,
        },
        "configuration": config.to_dict(),
        "definitions": {
            "duplicate_row": DUPLICATE_DEFINITION,
            "missing_value": MISSING_DEFINITION,
            "column_type": TYPE_DEFINITION,
            "outlier": OUTLIER_DEFINITION,
            "constant_column": CONSTANT_DEFINITION,
            "high_cardinality": HIGH_CARDINALITY_DEFINITION,
            "severity": SEVERITY_DEFINITION,
            "row_number": ROW_NUMBER_DEFINITION,
            "missingness_comparison": MISSINGNESS_COMPARISON,
            "high_cardinality_comparison": HIGH_CARDINALITY_COMPARISON,
            "outlier_comparison": OUTLIER_COMPARISON,
            "checks": dict(CHECK_CATALOG),
        },
    }


def _column_dict(column: ColumnProfile) -> dict[str, Any]:
    return {
        "name": column.name,
        "inferred_type": column.inferred_type,
        "dominant_type": column.dominant_type,
        "missing_count": column.missing_count,
        "missing_percentage": column.missing_percentage,
        "missing_fraction": column.missing_fraction,
        "missing_token_counts": column.missing_token_counts,
        "non_missing_count": column.non_missing_count,
        "unique_non_missing": column.unique_non_missing,
        "type_counts": column.type_counts,
        "unexpected_count": column.unexpected_count,
        "unexpected_distinct_count": column.unexpected_distinct_count,
        "unexpected_values": column.unexpected_values,
        "classification_note": column.classification_note,
        "numeric_summary": None
        if column.numeric_summary is None
        else _numeric_dict(column.numeric_summary),
        "categorical_summary": None
        if column.categorical_summary is None
        else _categorical_dict(column.categorical_summary),
    }


def _numeric_dict(summary: NumericSummary) -> dict[str, Any]:
    return {
        "count": summary.count,
        "minimum": summary.minimum,
        "maximum": summary.maximum,
        "mean": summary.mean,
        "mean_note": summary.mean_note,
        "excluded_non_numeric": summary.excluded_non_numeric,
        "outlier_assessment": summary.outlier_assessment,
        "outlier_assessment_note": summary.outlier_assessment_note,
    }


def _categorical_dict(summary: CategoricalSummary) -> dict[str, Any]:
    return {
        "unique_count": summary.unique_count,
        "most_frequent_value": summary.most_frequent_value,
        "most_frequent_count": summary.most_frequent_count,
        "most_frequent_percentage": summary.most_frequent_percentage,
        "value_truncated": summary.value_truncated,
    }


def _finding_dict(finding: QualityFinding) -> dict[str, Any]:
    return {
        "rule_id": finding.rule_id,
        "issue_title": finding.issue_title,
        "severity": finding.severity,
        "scope": finding.scope,
        "column": finding.column,
        "affected_records": finding.affected_records,
        "evidence": finding.evidence,
        "explanation": finding.explanation,
        "suggested_action": finding.suggested_action,
    }
