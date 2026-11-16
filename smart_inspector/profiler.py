"""Descriptive profiles: shape, missingness, duplicates, and column summaries.

Duplicate rows are counted with an explicit typed key. Pandas ``duplicated``
is not used because it treats ``True`` as equal to ``1``, which would hide a
type difference. Pandas still holds the aligned table and supplies its shape.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from smart_inspector.config import InspectionConfig
from smart_inspector.definitions import DUPLICATE_DEFINITION
from smart_inspector.inference import infer_column
from smart_inspector.models import (
    CategoricalSummary,
    ColumnProfile,
    DuplicateSummary,
    NumericSummary,
)
from smart_inspector.values import is_missing, report_scalar, value_identity

_MEAN_NOTE = (
    "Mean is unavailable because one or more values cannot be represented "
    "as finite floating-point numbers."
)


@dataclass
class ColumnSignals:
    """Public column profile plus the raw cells the quality rules still need."""

    profile: ColumnProfile
    raw_values: list[Any]
    numeric_values: list[int | float]
    numeric_rows: list[int]
    numeric_raw: list[Any]
    median_length: float | None


@dataclass
class DatasetProfile:
    """Everything the report and the quality engine need from one table."""

    columns: list[ColumnSignals]
    duplicates: DuplicateSummary
    row_count: int
    column_names: list[str]


def profile_dataset(frame: pd.DataFrame, config: InspectionConfig) -> DatasetProfile:
    """Profile each column and count exact duplicate rows."""
    row_count = int(frame.shape[0])
    column_names = [str(name) for name in frame.columns]
    tokens = set(config.missing_tokens)
    columns: list[ColumnSignals] = []
    for name in column_names:
        raw_values = frame[name].tolist()
        inferred = infer_column(raw_values, config)
        numeric_summary = _numeric_summary(inferred)
        profile = ColumnProfile(
            name=name,
            inferred_type=inferred.inferred_type,
            dominant_type=inferred.dominant_type,
            missing_count=inferred.missing_count,
            missing_percentage=inferred.missing_percentage,
            missing_fraction=inferred.missing_fraction,
            missing_token_counts=inferred.missing_token_counts,
            non_missing_count=inferred.non_missing_count,
            unique_non_missing=inferred.unique_non_missing,
            type_counts=inferred.type_counts,
            unexpected_count=inferred.unexpected_count,
            unexpected_distinct_count=inferred.unexpected_distinct_count,
            unexpected_values=inferred.unexpected_values,
            classification_note=inferred.classification_note,
            numeric_summary=numeric_summary,
            categorical_summary=_categorical_summary(
                inferred.inferred_type,
                raw_values,
                tokens,
            ),
        )
        columns.append(
            ColumnSignals(
                profile=profile,
                raw_values=raw_values,
                numeric_values=list(inferred.numeric_values),
                numeric_rows=list(inferred.numeric_rows),
                numeric_raw=list(inferred.numeric_raw),
                median_length=inferred.median_length,
            )
        )
    return DatasetProfile(
        columns=columns,
        duplicates=_duplicate_summary(columns, tokens),
        row_count=row_count,
        column_names=column_names,
    )


def _numeric_summary(inferred: Any) -> NumericSummary | None:
    if inferred.inferred_type not in {"integer", "float"}:
        return None
    values: list[int | float] = list(inferred.numeric_values)
    if not values:
        inferred.classification_note += (
            " No finite numeric observations could be parsed, so there is no numeric summary."
        )
        return None
    if any(isinstance(value, float) for value in values):
        minimum: int | float = float(min(values))
        maximum: int | float = float(max(values))
    else:
        minimum = min(values)
        maximum = max(values)
    mean, mean_note = _mean(values)
    return NumericSummary(
        count=len(values),
        minimum=minimum,
        maximum=maximum,
        mean=mean,
        mean_note=mean_note,
        excluded_non_numeric=inferred.non_missing_count - len(values),
    )


def _mean(values: list[int | float]) -> tuple[float | None, str | None]:
    try:
        array = np.asarray(values, dtype=float)
    except (OverflowError, ValueError):
        return None, _MEAN_NOTE
    if array.size == 0 or not np.isfinite(array).all():
        return None, _MEAN_NOTE
    return float(np.mean(array)), None


def _categorical_summary(
    inferred_type: str,
    raw_values: list[Any],
    tokens: set[str],
) -> CategoricalSummary | None:
    if inferred_type != "categorical":
        return None
    counts: dict[tuple[Any, ...], int] = {}
    first_value: dict[tuple[Any, ...], Any] = {}
    order: list[tuple[Any, ...]] = []
    for value in raw_values:
        if is_missing(value, tokens):
            continue
        identity = value_identity(value, tokens)
        if identity not in counts:
            counts[identity] = 0
            first_value[identity] = value
            order.append(identity)
        counts[identity] += 1
    if not order:
        return None
    winner = order[0]
    for identity in order:
        if counts[identity] > counts[winner]:
            winner = identity
    shown, truncated = report_scalar(first_value[winner])
    non_missing = sum(counts.values())
    return CategoricalSummary(
        unique_count=len(order),
        most_frequent_value=shown,
        most_frequent_count=counts[winner],
        most_frequent_percentage=(100.0 * counts[winner] / non_missing) if non_missing else 0.0,
        value_truncated=truncated,
    )


def _duplicate_summary(columns: list[ColumnSignals], tokens: set[str]) -> DuplicateSummary:
    if not columns:
        return DuplicateSummary(0, 0, 0, DUPLICATE_DEFINITION)
    row_count = len(columns[0].raw_values)
    keys = [
        tuple(value_identity(column.raw_values[index], tokens) for column in columns)
        for index in range(row_count)
    ]
    counts = Counter(keys)
    extra = sum(count - 1 for count in counts.values() if count > 1)
    rows_in_groups = sum(count for count in counts.values() if count > 1)
    groups = sum(1 for count in counts.values() if count > 1)
    return DuplicateSummary(
        extra_duplicate_rows=extra,
        rows_in_duplicate_groups=rows_in_groups,
        duplicate_group_count=groups,
        definition=DUPLICATE_DEFINITION,
    )
