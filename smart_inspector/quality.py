"""Six explainable data-quality checks.

The checks report evidence and a suggested action. They do not change the
table, impute values, or assign an overall quality score. Outlier findings
are information, not a claim that a value is wrong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from smart_inspector.config import ALL_CHECKS, InspectionConfig
from smart_inspector.models import QualityFinding
from smart_inspector.profiler import ColumnSignals, DatasetProfile
from smart_inspector.values import (
    SAMPLE_LIMIT,
    is_missing,
    report_scalar,
)

_MISSING_ERROR_FRACTION = 0.9

_DUPLICATE_ACTION = (
    "Review the duplicated rows with the data owner. Keep them if they are "
    "legitimate repeated observations. If they come from a join or an export, "
    "drop the extra copies before analysis. This tool does not delete rows."
)
_MISSING_ACTION = (
    "Confirm whether the missing values are expected. If the column is unused, "
    "exclude it from analysis. If the values should be present, check the export "
    "or the collection process. Do not impute until the reason is understood."
)
_MIXED_ACTION = (
    "Inspect the unexpected values in the evidence. Correct formatting errors, "
    "or split the column if it intentionally mixes different kinds of values. "
    "Do not convert the column automatically; that would hide the inconsistent records."
)
_OUTLIER_ACTION = (
    "Review the listed values in context. A statistical outlier can be a valid "
    "extreme measurement. Do not remove or winsorize these values unless you have "
    "a domain reason to treat them as errors."
)
_CONSTANT_ACTION = (
    "If the column is intentionally uniform, for example because a filter kept "
    "one site, you can ignore this finding. Otherwise it will not help distinguish "
    "records and may indicate a failed export."
)
_CARDINALITY_ACTION = (
    "Check whether this column is an identifier or a near-unique label rather than "
    "a category. High-cardinality fields can inflate grouped analyses. If it is an "
    "identifier, treat it as one and do not encode it as a categorical feature without a plan."
)


@dataclass(frozen=True)
class _Fences:
    q1: float
    q3: float
    iqr: float
    lower: float
    upper: float


def evaluate_quality(
    profiled: DatasetProfile,
    config: InspectionConfig,
) -> list[QualityFinding]:
    """Run the enabled checks and annotate numeric outlier status.

    Annotation updates ``numeric_summary`` in place so the report can say why
    an outlier check was skipped. The source table is not modified.
    """
    enabled = set(config.enabled_checks)
    findings: list[QualityFinding] = []
    if "missingness" in enabled:
        findings.extend(_missingness(profiled, config))
    if "duplicates" in enabled:
        findings.extend(_duplicates(profiled))
    if "mixed_types" in enabled:
        findings.extend(_mixed_types(profiled, config))
    findings.extend(_outliers(profiled, config, enabled="outliers" in enabled))
    if "constant_columns" in enabled:
        findings.extend(_constants(profiled, config))
    if "high_cardinality" in enabled:
        findings.extend(_high_cardinality(profiled, config))
    order = {rule: index for index, rule in enumerate(ALL_CHECKS)}
    column_order = {name: index for index, name in enumerate(profiled.column_names)}
    findings.sort(
        key=lambda finding: (
            order.get(finding.rule_id, len(order)),
            column_order.get(finding.column or "", -1),
        )
    )
    return findings


def _missingness(
    profiled: DatasetProfile,
    config: InspectionConfig,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for column in profiled.columns:
        profile = column.profile
        fraction = profile.missing_fraction
        if fraction <= config.missingness_threshold:
            continue
        severity = "error" if fraction >= _MISSING_ERROR_FRACTION else "warning"
        extent = (
            "At least 90% of the column is missing, so it is unlikely to support "
            "analysis without a documented reason."
            if severity == "error"
            else (
                "The column still has some observed values, but this amount of "
                "missingness can bias summaries and group comparisons."
            )
        )
        findings.append(
            QualityFinding(
                rule_id="missingness",
                issue_title=f"High missingness in column '{profile.name}'",
                severity=severity,
                scope="column",
                column=profile.name,
                affected_records=profile.missing_count,
                evidence={
                    "missing_count": profile.missing_count,
                    "non_missing_count": profile.non_missing_count,
                    "row_count": profiled.row_count,
                    "missing_fraction": profile.missing_fraction,
                    "missing_percentage": profile.missing_percentage,
                    "threshold": config.missingness_threshold,
                    "missing_tokens": profile.missing_token_counts,
                },
                explanation=(
                    f"{profile.missing_count} of {profiled.row_count} values "
                    f"({profile.missing_percentage:.2f}%) in column '{profile.name}' "
                    "are missing, which exceeds the configured threshold of "
                    f"{config.missingness_threshold:.2%} of rows. {extent}"
                ),
                suggested_action=_MISSING_ACTION,
            )
        )
    return findings


def _duplicates(profiled: DatasetProfile) -> list[QualityFinding]:
    summary = profiled.duplicates
    if summary.extra_duplicate_rows <= 0:
        return []
    return [
        QualityFinding(
            rule_id="duplicates",
            issue_title="Duplicate rows detected",
            severity="warning",
            scope="dataset",
            column=None,
            affected_records=summary.extra_duplicate_rows,
            evidence={
                "extra_duplicate_rows": summary.extra_duplicate_rows,
                "rows_in_duplicate_groups": summary.rows_in_duplicate_groups,
                "duplicate_group_count": summary.duplicate_group_count,
                "row_count": profiled.row_count,
            },
            explanation=(
                f"{_noun(summary.extra_duplicate_rows, 'extra row')} "
                f"{'is an exact copy' if summary.extra_duplicate_rows == 1 else 'are exact copies'} "
                "of an earlier row "
                f"({summary.rows_in_duplicate_groups} "
                f"{'row sits' if summary.rows_in_duplicate_groups == 1 else 'rows sit'} in "
                f"{_noun(summary.duplicate_group_count, 'duplicated group')}). "
                "Exact means every column matches, with all missing representations treated as equal "
                "and with text and types compared exactly. Duplicates can be legitimate repeated "
                "measurements or an export problem. This finding does not by itself prove the rows are wrong."
            ),
            suggested_action=_DUPLICATE_ACTION,
        )
    ]


def _mixed_types(
    profiled: DatasetProfile,
    config: InspectionConfig,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for column in profiled.columns:
        profile = column.profile
        if profile.non_missing_count == 0 or profile.unexpected_count == 0:
            continue
        mixed = profile.inferred_type == "mixed"
        fraction = profile.unexpected_count / profile.non_missing_count
        if mixed:
            why = (
                f"No type reached the dominance threshold of {config.dominance_threshold:.0%}. "
                f"The closest type is {profile.dominant_type}, and "
                f"{_mismatch(profile.unexpected_count, profile.non_missing_count, fraction)} "
                "The column is therefore mixed rather than coerced."
            )
        else:
            why = (
                f"The column was accepted as {profile.inferred_type} because "
                f"{profile.dominant_type} is the dominant type, but "
                f"{_mismatch(profile.unexpected_count, profile.non_missing_count, fraction)} "
                "Those values were not converted."
            )
        sample = profile.unexpected_values
        shown_cells = sum(int(item.get("count", 0)) for item in sample)
        sample_truncated = profile.unexpected_count > shown_cells or any(
            bool(item.get("truncated")) for item in sample
        )
        findings.append(
            QualityFinding(
                rule_id="mixed_types",
                issue_title=f"Inconsistent values in column '{profile.name}'",
                severity="error" if mixed else "warning",
                scope="column",
                column=profile.name,
                affected_records=profile.unexpected_count,
                evidence={
                    "inferred_type": profile.inferred_type,
                    "dominant_type": profile.dominant_type,
                    "unexpected_count": profile.unexpected_count,
                    "unexpected_distinct_count": profile.unexpected_distinct_count,
                    "non_missing_count": profile.non_missing_count,
                    "unexpected_fraction": fraction,
                    "dominance_threshold": config.dominance_threshold,
                    "type_counts": profile.type_counts,
                    "sample_values": sample,
                    "sample_limit": SAMPLE_LIMIT,
                    "sample_truncated": sample_truncated,
                },
                explanation=why,
                suggested_action=_MIXED_ACTION,
            )
        )
    return findings


def _outliers(
    profiled: DatasetProfile,
    config: InspectionConfig,
    *,
    enabled: bool,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for column in profiled.columns:
        summary = column.profile.numeric_summary
        if summary is None:
            continue
        if not enabled:
            summary.outlier_assessment = "disabled"
            summary.outlier_assessment_note = (
                "The outliers check is turned off in the inspection configuration."
            )
            continue
        count = len(column.numeric_values)
        if count < config.outlier_min_samples:
            summary.outlier_assessment = "skipped_too_few_values"
            summary.outlier_assessment_note = (
                f"Outlier detection needs at least {config.outlier_min_samples} numeric values; "
                f"this column has {count}."
            )
            continue
        fences = _fences(column.numeric_values, config.outlier_multiplier)
        if fences is None:
            summary.outlier_assessment = "skipped_non_finite"
            summary.outlier_assessment_note = (
                "Outlier detection was skipped because the numeric values cannot all "
                "be converted to finite floats."
            )
            continue
        summary.outlier_assessment = "completed"
        summary.outlier_assessment_note = None
        outliers = _collect_outliers(column, fences)
        if not outliers:
            continue
        sample = outliers[:SAMPLE_LIMIT]
        iqr_note = ""
        if fences.iqr == 0:
            iqr_note = (
                " The interquartile range is 0, so any value different from the quartile "
                "is outside the fences."
            )
        findings.append(
            QualityFinding(
                rule_id="outliers",
                issue_title=f"Potential numerical outliers in column '{column.profile.name}'",
                severity="info",
                scope="column",
                column=column.profile.name,
                affected_records=len(outliers),
                evidence={
                    "method": "iqr",
                    "multiplier": config.outlier_multiplier,
                    "sample_size": count,
                    "q1": fences.q1,
                    "q3": fences.q3,
                    "iqr": fences.iqr,
                    "lower_bound": fences.lower,
                    "upper_bound": fences.upper,
                    "outlier_count": len(outliers),
                    "sample_values": sample,
                    "sample_limit": SAMPLE_LIMIT,
                    "sample_truncated": len(outliers) > SAMPLE_LIMIT,
                    "note": (
                        "Values outside the fences are potential anomalies, not confirmed data errors."
                    ),
                },
                explanation=(
                    f"{_noun(len(outliers), 'numeric value')} in column '{column.profile.name}' "
                    f"{'falls' if len(outliers) == 1 else 'fall'} strictly "
                    f"outside the Tukey fences [{_num(fences.lower)}, {_num(fences.upper)}] "
                    f"(Q1={_num(fences.q1)}, Q3={_num(fences.q3)}, IQR={_num(fences.iqr)}, "
                    f"multiplier={config.outlier_multiplier}). "
                    "These are potential outliers, not confirmed data errors. A real extreme "
                    "measurement can fall outside the fences, and the fences can also be tight "
                    "when the interquartile range is small."
                    + iqr_note
                ),
                suggested_action=_OUTLIER_ACTION,
            )
        )
    return findings


def _constants(profiled: DatasetProfile, config: InspectionConfig) -> list[QualityFinding]:
    tokens = set(config.missing_tokens)
    findings: list[QualityFinding] = []
    for column in profiled.columns:
        profile = column.profile
        if profile.unique_non_missing != 1:
            continue
        constant = next(
            value for value in column.raw_values if not is_missing(value, tokens)
        )
        shown, truncated = report_scalar(constant)
        findings.append(
            QualityFinding(
                rule_id="constant_columns",
                issue_title=f"Constant column '{profile.name}'",
                severity="warning",
                scope="column",
                column=profile.name,
                affected_records=profile.non_missing_count,
                evidence={
                    "constant_value": shown,
                    "value_truncated": truncated,
                    "non_missing_count": profile.non_missing_count,
                    "missing_count": profile.missing_count,
                    "unique_non_missing": 1,
                },
                explanation=(
                    f"Column '{profile.name}' has a single distinct non-missing value "
                    f"({_quote(shown)}). {_noun(profile.non_missing_count, 'observed row')} "
                    f"{'shares' if profile.non_missing_count == 1 else 'share'} it "
                    f"and {_noun(profile.missing_count, 'row')} "
                    f"{'is' if profile.missing_count == 1 else 'are'} missing. A constant column does not "
                    "distinguish records. It can be intentional, for example after a filter, "
                    "or a sign that the export filled one value."
                ),
                suggested_action=_CONSTANT_ACTION,
            )
        )
    return findings


def _high_cardinality(
    profiled: DatasetProfile,
    config: InspectionConfig,
) -> list[QualityFinding]:
    findings: list[QualityFinding] = []
    for column in profiled.columns:
        profile = column.profile
        if profile.inferred_type != "categorical":
            continue
        unique = profile.unique_non_missing
        observed = profile.non_missing_count
        if observed == 0 or unique < 2:
            continue
        ratio = unique / observed
        if ratio < config.high_cardinality_threshold:
            continue
        median = column.median_length
        findings.append(
            QualityFinding(
                rule_id="high_cardinality",
                issue_title=f"High cardinality in column '{profile.name}'",
                severity="info",
                scope="column",
                column=profile.name,
                affected_records=unique,
                evidence={
                    "unique_count": unique,
                    "non_missing_count": observed,
                    "distinct_ratio": ratio,
                    "threshold": config.high_cardinality_threshold,
                    "median_value_length": median,
                    "categorical_max_length": config.categorical_max_length,
                    "affected_records_meaning": "distinct non-missing values",
                },
                explanation=(
                    f"Column '{profile.name}' is categorical and has {unique} distinct values "
                    f"out of {observed} observed values (distinct-value ratio {ratio:.2f}), "
                    f"which is at or above the threshold of {config.high_cardinality_threshold:.2f}. "
                    "Affected records here means the number of distinct values, not a count of bad rows. "
                    "A high ratio often means the column is an identifier or a near-unique label rather "
                    "than a useful category. It is not evidence that the values are incorrect. "
                    "Small columns can cross the threshold with only a few distinct labels."
                ),
                suggested_action=_CARDINALITY_ACTION,
            )
        )
    return findings


def _fences(values: list[int | float], multiplier: float) -> _Fences | None:
    try:
        array = np.asarray(values, dtype=float)
    except (OverflowError, ValueError):
        return None
    if array.size == 0 or not np.isfinite(array).all():
        return None
    q1 = float(np.quantile(array, 0.25, method="linear"))
    q3 = float(np.quantile(array, 0.75, method="linear"))
    if not math.isfinite(q1) or not math.isfinite(q3):
        return None
    iqr = q3 - q1
    return _Fences(
        q1=q1,
        q3=q3,
        iqr=iqr,
        lower=q1 - multiplier * iqr,
        upper=q3 + multiplier * iqr,
    )


def _collect_outliers(column: ColumnSignals, fences: _Fences) -> list[dict[str, object]]:
    try:
        array = np.asarray(column.numeric_values, dtype=float)
    except (OverflowError, ValueError):
        return []
    records: list[dict[str, object]] = []
    for index, numeric in enumerate(array.tolist()):
        if numeric < fences.lower:
            distance = fences.lower - numeric
        elif numeric > fences.upper:
            distance = numeric - fences.upper
        else:
            continue
        shown, truncated = report_scalar(column.numeric_raw[index])
        records.append(
            {
                "row": column.numeric_rows[index],
                "value": shown,
                "numeric_value": float(numeric),
                "distance_outside_fence": float(distance),
                "truncated": truncated,
            }
        )
    records.sort(
        key=lambda item: (
            -float(item["distance_outside_fence"]),
            int(item["row"]),
        )
    )
    return records


def _noun(count: int, singular: str) -> str:
    """Return ``count`` plus a singular or plural noun."""
    if count == 1:
        return f"1 {singular}"
    return f"{count} {singular}s"


def _mismatch(unexpected: int, observed: int, fraction: float) -> str:
    verb = "does not match" if unexpected == 1 else "do not match"
    return (
        f"{unexpected} of {observed} non-missing values ({fraction:.2%}) {verb} it."
    )


def _num(value: float) -> str:
    return f"{value:.6g}"


def _quote(value: object) -> str:
    if isinstance(value, str):
        return repr(value)
    return str(value)
