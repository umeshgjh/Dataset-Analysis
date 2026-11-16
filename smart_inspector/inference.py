"""Column type inference that does not rewrite the source values.

A column receives a type only when one compatible kind covers at least the
dominance threshold. Anything else is ``mixed``, and the values that do not
fit are returned for the report. String columns are then split into short
categorical labels and free text.

Short code columns are the exception. When integer-like tokens sit beside text
codes that contain both letters and digits, and those codes use more than one
alphabetic pattern, the column is categorical. An integer or float column that
already meets the dominance threshold is left numeric.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

import numpy as np

from smart_inspector.config import InspectionConfig
from smart_inspector.values import (
    DOMINANT_PRIORITY,
    KIND_ORDER,
    REPORT_TEXT_LIMIT,
    SAMPLE_LIMIT,
    clip_text,
    compatible,
    datetime_pattern,
    display_value,
    is_missing,
    missing_label,
    parse_numeric,
    value_identity,
    value_kind,
)


@dataclass
class InferenceResult:
    """Type decision and the numeric values that may be summarized."""

    inferred_type: str
    dominant_type: str
    missing_count: int
    missing_fraction: float
    missing_percentage: float
    missing_token_counts: dict[str, int]
    non_missing_count: int
    unique_non_missing: int
    type_counts: dict[str, int]
    unexpected_count: int
    unexpected_distinct_count: int
    unexpected_values: list[dict[str, Any]]
    classification_note: str
    numeric_values: list[int | float]
    numeric_rows: list[int]
    numeric_raw: list[Any]
    median_length: float | None


def infer_column(values: list[Any], config: InspectionConfig) -> InferenceResult:
    """Infer a type for one column without modifying ``values``."""
    tokens = set(config.missing_tokens)
    row_count = len(values)
    token_counts: Counter[str] = Counter()
    observed: list[tuple[int, Any, str]] = []
    for row_number, value in enumerate(values, start=1):
        if is_missing(value, tokens):
            token_counts[missing_label(value)] += 1
            continue
        kind = value_kind(value)
        if kind is None:
            token_counts[missing_label(value)] += 1
            continue
        observed.append((row_number, value, kind))

    missing_count = row_count - len(observed)
    fraction = (missing_count / row_count) if row_count else 0.0
    type_counts = {kind: 0 for kind in KIND_ORDER}
    for _row, _value, kind in observed:
        type_counts[kind] += 1
    unique_non_missing = len({value_identity(value, tokens) for _row, value, _kind in observed})
    token_map = dict(sorted(token_counts.items()))

    if not observed:
        return InferenceResult(
            inferred_type="unknown",
            dominant_type="unknown",
            missing_count=missing_count,
            missing_fraction=fraction,
            missing_percentage=fraction * 100.0,
            missing_token_counts=token_map,
            non_missing_count=0,
            unique_non_missing=0,
            type_counts=type_counts,
            unexpected_count=0,
            unexpected_distinct_count=0,
            unexpected_values=[],
            classification_note="Every value is missing, so the column type is unknown.",
            numeric_values=[],
            numeric_rows=[],
            numeric_raw=[],
            median_length=None,
        )

    kinds = [kind for _row, _value, kind in observed]
    dominant = _choose_dominant(kinds)
    covered = sum(1 for kind in kinds if compatible(dominant, kind))
    unexpected_rows = [
        (row_number, value, kind)
        for row_number, value, kind in observed
        if not compatible(dominant, kind)
    ]
    unexpected_values, unexpected_count, unexpected_distinct_count = _unexpected_samples(
        unexpected_rows
    )
    coverage = covered / len(observed)
    accepted = coverage + 0.0 >= config.dominance_threshold

    median_length: float | None = None
    multiline = False
    format_note = ""
    if accepted and dominant == "string":
        inferred, median_length, multiline = _classify_text(observed, config)
    elif accepted:
        inferred = dominant
        if dominant == "datetime":
            format_note = _datetime_format_note(observed)
    else:
        inferred = "mixed"

    codes = _code_column(observed, config)
    numeric_accepted = accepted and dominant in {"integer", "float"}
    if codes is not None and not numeric_accepted:
        inferred = "categorical"
        median_length = codes.median_length
        multiline = False
        format_note = ""
        unexpected_values = []
        unexpected_count = 0
        unexpected_distinct_count = 0
        note = _code_column_note(
            dominant=dominant,
            covered=covered,
            non_missing=len(observed),
            threshold=config.dominance_threshold,
            accepted_text=accepted and dominant == "string",
            codes=codes,
            max_length=config.categorical_max_length,
        )
    else:
        note = _classification_note(
            inferred=inferred,
            dominant=dominant,
            covered=covered,
            non_missing=len(observed),
            threshold=config.dominance_threshold,
            type_counts=type_counts,
            unexpected_count=unexpected_count,
            median_length=median_length,
            max_length=config.categorical_max_length,
            multiline=multiline,
            format_note=format_note,
        )
    numeric_values: list[int | float] = []
    numeric_rows: list[int] = []
    numeric_raw: list[Any] = []
    if inferred in {"integer", "float"}:
        for row_number, value, kind in observed:
            if not compatible(dominant, kind):
                continue
            parsed = parse_numeric(value)
            if parsed is None:
                continue
            numeric_values.append(parsed)
            numeric_rows.append(row_number)
            numeric_raw.append(value)

    return InferenceResult(
        inferred_type=inferred,
        dominant_type=dominant,
        missing_count=missing_count,
        missing_fraction=fraction,
        missing_percentage=fraction * 100.0,
        missing_token_counts=token_map,
        non_missing_count=len(observed),
        unique_non_missing=unique_non_missing,
        type_counts=type_counts,
        unexpected_count=unexpected_count,
        unexpected_distinct_count=unexpected_distinct_count,
        unexpected_values=unexpected_values,
        classification_note=note,
        numeric_values=numeric_values,
        numeric_rows=numeric_rows,
        numeric_raw=numeric_raw,
        median_length=median_length,
    )


@dataclass(frozen=True)
class _CodeColumn:
    """Evidence that a short-token column is a code set rather than a measurement."""

    median_length: float
    integer_count: int
    string_count: int
    shape_count: int
    examples: tuple[str, ...]


def _code_column(
    observed: list[tuple[int, Any, str]],
    config: InspectionConfig,
) -> _CodeColumn | None:
    """Detect short codes that mix integer-like tokens with letter-and-digit labels.

    The alphabetic pattern of a code is the letters that remain after digits and
    signs are removed. One repeated pattern, such as ``bad0`` and ``bad1``, is
    not enough: that shape is left on the ordinary mixed or numeric path. Two
    different patterns are required. Floats, booleans, dates, whitespace, and
    tokens longer than the categorical limit also decline the exception.
    """
    lengths: list[int] = []
    integer_count = 0
    string_count = 0
    compound_counts: Counter[str] = Counter()
    shapes: set[str] = set()
    limit = config.categorical_max_length
    for _row_number, value, kind in observed:
        if kind not in {"integer", "string"}:
            return None
        text = value.strip() if isinstance(value, str) else str(value)
        if text == "" or any(character.isspace() for character in text):
            return None
        if len(text) > limit:
            return None
        lengths.append(len(text))
        if kind == "integer":
            integer_count += 1
            continue
        string_count += 1
        if not any(character.isalpha() for character in text):
            return None
        if not any(character.isdigit() for character in text):
            continue
        shape = "".join(character.lower() for character in text if character.isalpha())
        if shape == "":
            return None
        shapes.add(shape)
        compound_counts[text] += 1
    if integer_count < 1 or len(shapes) < 2 or not lengths:
        return None
    examples = tuple(value for value, _count in compound_counts.most_common(3))
    median_length = float(np.median(np.asarray(lengths, dtype=float)))
    return _CodeColumn(
        median_length=median_length,
        integer_count=integer_count,
        string_count=string_count,
        shape_count=len(shapes),
        examples=examples,
    )


def _code_column_note(
    *,
    dominant: str,
    covered: int,
    non_missing: int,
    threshold: float,
    accepted_text: bool,
    codes: _CodeColumn,
    max_length: int,
) -> str:
    """Explain why integer-like tokens were kept as category labels."""
    percent = 100.0 * covered / non_missing
    shown = ", ".join(repr(example) for example in codes.examples)
    integer_word = "value is" if codes.integer_count == 1 else "values are"
    text_word = "is" if codes.string_count == 1 else "are"
    pattern_word = "pattern" if codes.shape_count == 1 else "patterns"
    sentences = [
        (
            "Classified as categorical because the values are short codes rather than "
            f"measurements. {codes.integer_count} non-missing {integer_word} integer-like and "
            f"{codes.string_count} {text_word} text. The letter-and-digit codes use "
            f"{codes.shape_count} different alphabetic {pattern_word}, including {shown}."
        ),
        (
            "Those patterns are different, so the integer-like tokens stay in the same "
            "label set. They are not listed as unexpected, and numeric summaries are omitted "
            "so a mean is not reported for codes."
        ),
    ]
    if accepted_text:
        sentences.append(
            f"Text covers {covered} of {non_missing} non-missing values ({percent:.2f}%), "
            f"which meets the dominance threshold of {threshold:.0%}. The integer-like "
            "labels are still part of the category."
        )
    else:
        sentences.append(
            f"The closest single kind is {dominant}, covering {covered} of {non_missing} "
            f"non-missing values ({percent:.2f}%), below the dominance threshold of "
            f"{threshold:.0%}. The column is categorical rather than mixed because the "
            "two forms belong to one code set."
        )
    sentences.append(
        f"Median label length is {codes.median_length:.1f} characters, within the limit "
        f"of {max_length}."
    )
    return " ".join(sentences)


def _choose_dominant(kinds: list[str]) -> str:
    """Pick the compatible type with the widest coverage.

    On a tie, the earlier entry in ``DOMINANT_PRIORITY`` wins. Float coverage
    includes integers, so a float wins that tie only when its coverage is
    strictly larger, which happens when a non-integral float is present.
    """
    best = "string"
    best_coverage = -1
    for candidate in DOMINANT_PRIORITY:
        coverage = sum(1 for kind in kinds if compatible(candidate, kind))
        if coverage > best_coverage:
            best = candidate
            best_coverage = coverage
    return best


def _unexpected_samples(
    rows: list[tuple[int, Any, str]],
) -> tuple[list[dict[str, Any]], int, int]:
    grouped: dict[tuple[Any, ...], dict[str, Any]] = {}
    total = 0
    for row_number, value, kind in rows:
        total += 1
        identity = _unexpected_identity(value, kind)
        if identity not in grouped:
            shown, truncated = clip_text(display_value(value), REPORT_TEXT_LIMIT)
            grouped[identity] = {
                "value": shown,
                "kind": kind,
                "count": 0,
                "first_row": row_number,
                "truncated": truncated,
            }
        grouped[identity]["count"] += 1
    ordered = sorted(
        grouped.values(),
        key=lambda item: (-int(item["count"]), int(item["first_row"]), str(item["value"])),
    )
    return ordered[:SAMPLE_LIMIT], total, len(grouped)


def _unexpected_identity(value: Any, kind: str) -> tuple[Any, ...]:
    """Group unexpected cells without treating ``True`` as ``1`` or ``"1"``."""
    if isinstance(value, str):
        return ("str", kind, value)
    if isinstance(value, bool):
        return ("bool", value)
    if isinstance(value, int):
        return ("int", value)
    if isinstance(value, float):
        return ("float", value)
    return ("other", kind, display_value(value))


def _classify_text(
    observed: list[tuple[int, Any, str]],
    config: InspectionConfig,
) -> tuple[str, float, bool]:
    lengths: list[int] = []
    multiline = False
    for _row, value, kind in observed:
        if kind != "string" or not isinstance(value, str):
            continue
        if "\n" in value or "\r" in value:
            multiline = True
        lengths.append(len(value.strip()))
    if not lengths:
        return "string", 0.0, multiline
    median_length = float(np.median(np.asarray(lengths, dtype=float)))
    if multiline or median_length > config.categorical_max_length:
        return "string", median_length, multiline
    return "categorical", median_length, multiline


def _datetime_format_note(observed: list[tuple[int, Any, str]]) -> str:
    counts: dict[str, int] = {}
    for _row, value, kind in observed:
        if kind != "datetime" or not isinstance(value, str):
            continue
        label = datetime_pattern(value)
        counts[label] = counts.get(label, 0) + 1
    if len(counts) < 2:
        return ""
    listed = ", ".join(f"{name} ({count})" for name, count in counts.items())
    return f"More than one datetime format is present: {listed}."


def _classification_note(
    *,
    inferred: str,
    dominant: str,
    covered: int,
    non_missing: int,
    threshold: float,
    type_counts: dict[str, int],
    unexpected_count: int,
    median_length: float | None,
    max_length: int,
    multiline: bool,
    format_note: str,
) -> str:
    percent = 100.0 * covered / non_missing
    if inferred == "mixed":
        return (
            f"Classified as mixed because the dominant type {dominant} covers "
            f"{covered} of {non_missing} non-missing values ({percent:.2f}%), "
            f"below the dominance threshold of {threshold:.0%}. "
            "Unexpected values are listed separately. Numeric summaries are omitted "
            "for mixed columns so a mean is not reported for an unstable type."
        )

    if unexpected_count == 0 and dominant == "integer":
        lead = "Accepted as integer because every non-missing value is an integer."
    elif unexpected_count == 0 and dominant == "float":
        if type_counts["integer"]:
            lead = (
                "Accepted as float because every non-missing value is numeric "
                "and at least one is a float."
            )
        else:
            lead = "Accepted as float because every non-missing value is a float."
    elif unexpected_count == 0 and dominant == "boolean":
        lead = (
            "Accepted as boolean because every non-missing value is a JSON boolean "
            "or one of true, false, yes, and no."
        )
    elif unexpected_count == 0 and dominant == "datetime":
        lead = (
            "Accepted as datetime because every non-missing value matches an "
            "unambiguous year-first date or timestamp."
        )
    elif unexpected_count == 0 and dominant == "string":
        lead = "Accepted as string because every non-missing value is text."
    else:
        lead = (
            f"Accepted as {dominant} because that type covers {covered} of "
            f"{non_missing} non-missing values ({percent:.2f}%), which meets "
            f"the dominance threshold of {threshold:.0%}."
        )

    sentences = [lead]
    if inferred == "categorical" and median_length is not None:
        sentences.append(
            "Classified as categorical because the values are short labels "
            f"(median length {median_length:.1f} characters, limit {max_length}) "
            "and none contain a newline."
        )
    elif inferred == "string" and median_length is not None:
        if multiline:
            sentences.append(
                "Classified as free text rather than categorical because at least "
                "one value contains a newline."
            )
        else:
            sentences.append(
                "Classified as free text rather than categorical because the median "
                f"value length is {median_length:.1f} characters, above the label "
                f"limit of {max_length}."
            )
    if unexpected_count == 1:
        sentences.append(
            f"1 non-missing value does not match {dominant} and is reported as unexpected."
        )
    elif unexpected_count:
        sentences.append(
            f"{unexpected_count} non-missing values do not match {dominant} "
            "and are reported as unexpected."
        )
    if format_note:
        sentences.append(format_note)
    return " ".join(sentences)
