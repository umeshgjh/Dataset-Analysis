"""Markdown renderer.

The renderer reads the same payload as the JSON report and only changes
presentation: headings, tables, and rounded numbers.
"""

from __future__ import annotations

import math
from typing import Any

_PERCENT_POINT_KEYS = {"missing_percentage", "most_frequent_percentage"}
_FRACTION_KEYS = {
    "missing_fraction",
    "unexpected_fraction",
    "distinct_ratio",
    "threshold",
    "dominance_threshold",
    "missingness_threshold",
    "high_cardinality_threshold",
}


def render_markdown(payload: dict[str, Any]) -> str:
    """Render a complete inspection report."""
    sections = [
        _header(payload),
        _input_file(payload),
        _overview(payload),
        _column_types(payload),
        _missing(payload),
        _duplicates(payload),
        _numeric(payload),
        _categorical(payload),
        _findings(payload),
        _configuration(payload),
        _definitions(payload),
    ]
    return "\n\n".join(section.strip("\n") for section in sections) + "\n"


def _header(payload: dict[str, Any]) -> str:
    tool = payload["tool"]
    overview = payload["overview"]
    counts = payload["finding_counts"]
    duplicates = payload["duplicates"]["extra_duplicate_rows"]
    name = payload["input_file"]["name"]
    lines = [
        "# Data Inspection Report",
        "",
        (
            f"**{tool['name']} {tool['version']}** inspected `{name}` "
            f"at {payload['inspected_at']}."
        ),
        "",
        (
            "Severities distinguish consistency problems (`error`) from issues that "
            "may still be legitimate (`warning`) and potential anomalies that are not "
            "evidence a value is wrong (`info`). Statistical outliers are never treated "
            "as confirmed errors. This report does not include an overall quality score "
            "and it does not change the source file."
        ),
        "",
        _kv_table(
            [
                ("Rows", overview["row_count"]),
                ("Columns", overview["column_count"]),
                ("Extra duplicate rows", duplicates),
                (
                    "Findings",
                    (
                        f"{counts['total']} "
                        f"(error: {counts['error']}, warning: {counts['warning']}, "
                        f"info: {counts['info']})"
                    ),
                ),
            ]
        ),
    ]
    return "\n".join(lines)


def _input_file(payload: dict[str, Any]) -> str:
    info = payload["input_file"]
    runtime = payload["runtime"]
    rows = [
        ("Path", f"`{info['path']}`"),
        ("Absolute path", f"`{info['absolute_path']}`"),
        ("Format", info["format"]),
        ("Size", f"{info['size_bytes']} bytes"),
        ("Encoding", info["encoding"] or "unspecified"),
        ("Python", runtime["python"]),
        ("pandas", runtime["pandas"]),
        ("NumPy", runtime["numpy"]),
    ]
    return "## Input File\n\n" + _kv_table(rows)


def _overview(payload: dict[str, Any]) -> str:
    names = ", ".join(f"`{_inline(name)}`" for name in payload["overview"]["column_names"])
    return "\n".join(
        [
            "## Dataset Overview",
            "",
            (
                f"The table has {payload['overview']['row_count']} rows and "
                f"{payload['overview']['column_count']} columns."
            ),
            "",
            f"Column names, in file order: {names}.",
        ]
    )


def _column_types(payload: dict[str, Any]) -> str:
    lines = [
        "## Column Types",
        "",
        (
            "Types are inferred from the non-missing values. `dominant_type` is the "
            "kind used to decide which values are unexpected. `inferred_type` is "
            "`categorical` or `string` for an accepted text column, `mixed` when no "
            "kind is stable, and `unknown` when every value is missing."
        ),
        "",
        _table(
            ["Column", "Inferred type", "Dominant type", "Unique", "Unexpected"],
            [
                [
                    column["name"],
                    column["inferred_type"],
                    column["dominant_type"],
                    column["unique_non_missing"],
                    column["unexpected_count"],
                ]
                for column in payload["columns"]
            ],
        ),
        "",
        "### Classification notes",
        "",
    ]
    for column in payload["columns"]:
        lines.append(f"- `{_inline(column['name'])}`: {column['classification_note']}")
    return "\n".join(lines)


def _missing(payload: dict[str, Any]) -> str:
    lines = [
        "## Missing-Value Analysis",
        "",
        payload["definitions"]["missing_value"],
        "",
        _table(
            ["Column", "Missing", "Missing %", "Non-missing", "Missing tokens"],
            [
                [
                    column["name"],
                    column["missing_count"],
                    _percent_points(column["missing_percentage"]),
                    column["non_missing_count"],
                    _token_text(column["missing_token_counts"]),
                ]
                for column in payload["columns"]
            ],
        ),
    ]
    return "\n".join(lines)


def _duplicates(payload: dict[str, Any]) -> str:
    duplicates = payload["duplicates"]
    lines = [
        "## Duplicate Rows",
        "",
        duplicates["definition"],
        "",
        _kv_table(
            [
                ("Extra duplicate rows", duplicates["extra_duplicate_rows"]),
                ("Rows in duplicate groups", duplicates["rows_in_duplicate_groups"]),
                ("Duplicate groups", duplicates["duplicate_group_count"]),
            ]
        ),
    ]
    return "\n".join(lines)


def _numeric(payload: dict[str, Any]) -> str:
    lines = ["## Numeric Summaries", ""]
    summaries = payload["numeric_summaries"]
    if not summaries:
        lines.append(
            "No numeric columns were inferred. Integer and float columns appear here "
            "only after a dominant numeric type is accepted. Mixed columns are omitted "
            "so a mean is not reported for an unstable type."
        )
        return "\n".join(lines)
    lines.append(
        "Minimum, maximum, and mean use only values compatible with the accepted "
        "numeric type. Excluded cells are non-numeric values left out of those statistics. "
        "Markdown shows numbers to 6 decimal places; the JSON report keeps full precision."
    )
    lines.append("")
    lines.append(
        _table(
            [
                "Column",
                "Count",
                "Minimum",
                "Maximum",
                "Mean",
                "Excluded",
                "Outlier check",
            ],
            [
                [
                    item["column"],
                    item["count"],
                    _fmt(item["minimum"]),
                    _fmt(item["maximum"]),
                    _fmt(item["mean"]) if item["mean"] is not None else "unavailable",
                    item["excluded_non_numeric"],
                    item["outlier_assessment"],
                ]
                for item in summaries
            ],
        )
    )
    notes = [
        f"- `{_inline(item['column'])}`: {item['outlier_assessment_note']}"
        for item in summaries
        if item.get("outlier_assessment_note")
    ]
    mean_notes = [
        f"- `{_inline(item['column'])}`: {item['mean_note']}"
        for item in summaries
        if item.get("mean_note")
    ]
    if notes or mean_notes:
        lines.extend(["", *mean_notes, *notes])
    return "\n".join(lines)


def _categorical(payload: dict[str, Any]) -> str:
    lines = ["## Categorical Summaries", ""]
    summaries = payload["categorical_summaries"]
    if not summaries:
        lines.append(
            "No categorical columns were inferred. Boolean, datetime, numeric, "
            "free-text, mixed, and unknown columns are not given a mode here. "
            "Their unique counts are still listed under Column Types."
        )
        return "\n".join(lines)
    lines.append(
        "The most frequent value is the first non-missing value that reaches the "
        "highest count. Ties keep the value that appears earliest in the file. "
        "The share is the count divided by non-missing values."
    )
    lines.append("")
    lines.append(
        _table(
            ["Column", "Unique values", "Most frequent", "Count", "Share of non-missing"],
            [
                [
                    item["column"],
                    item["unique_count"],
                    _fmt(item["most_frequent_value"])
                    + (" (truncated)" if item["value_truncated"] else ""),
                    item["most_frequent_count"],
                    _percent_points(item["most_frequent_percentage"]),
                ]
                for item in summaries
            ],
        )
    )
    return "\n".join(lines)


def _findings(payload: dict[str, Any]) -> str:
    lines = ["## Data-Quality Findings", ""]
    counts = payload["finding_counts"]
    lines.append(
        f"{counts['total']} finding(s): {counts['error']} error, "
        f"{counts['warning']} warning, {counts['info']} info."
    )
    findings = payload["findings"]
    if not findings:
        lines.extend(
            [
                "",
                "No data-quality findings were raised for the enabled checks. "
                "Descriptive sections above are still the inspection result.",
            ]
        )
        return "\n".join(lines)
    for index, finding in enumerate(findings, start=1):
        target = finding["column"] if finding["column"] is not None else "dataset"
        affected = (
            "not applicable"
            if finding["affected_records"] is None
            else str(finding["affected_records"])
        )
        lines.extend(
            [
                "",
                f"### {index}. {finding['issue_title']}",
                "",
                _kv_table(
                    [
                        ("Rule", finding["rule_id"]),
                        ("Severity", finding["severity"]),
                        ("Scope", finding["scope"]),
                        ("Affected column or dataset", target),
                        ("Affected records", affected),
                    ]
                ),
                "",
                _evidence(finding["evidence"]),
                "",
                "**Why this was flagged**",
                "",
                finding["explanation"],
                "",
                "**Suggested action**",
                "",
                finding["suggested_action"],
            ]
        )
    return "\n".join(lines)


def _configuration(payload: dict[str, Any]) -> str:
    config = payload["configuration"]
    rows = [
        ("Missingness threshold", _fmt(config["missingness_threshold"])),
        ("Outlier method", config["outlier_method"]),
        ("Outlier multiplier", _fmt(config["outlier_multiplier"])),
        ("Outlier minimum samples", config["outlier_min_samples"]),
        ("High-cardinality threshold", _fmt(config["high_cardinality_threshold"])),
        ("Categorical maximum length", config["categorical_max_length"]),
        ("Dominance threshold", _fmt(config["dominance_threshold"])),
        ("Enabled checks", ", ".join(config["enabled_checks"]) or "none"),
        ("Disabled checks", ", ".join(config["disabled_checks"]) or "none"),
        ("Missing tokens", ", ".join(config["missing_tokens"]) or "none"),
    ]
    return "\n".join(
        [
            "## Inspection Configuration",
            "",
            "These are the settings that produced this report.",
            "",
            _kv_table(rows),
            "",
            payload["definitions"]["missingness_comparison"],
            "",
            payload["definitions"]["high_cardinality_comparison"],
            "",
            payload["definitions"]["outlier_comparison"],
        ]
    )


def _definitions(payload: dict[str, Any]) -> str:
    definitions = payload["definitions"]
    checks = definitions["checks"]
    lines = [
        "## Definitions",
        "",
        f"**Duplicate row.** {definitions['duplicate_row']}",
        "",
        f"**Missing value.** {definitions['missing_value']}",
        "",
        f"**Column type.** {definitions['column_type']}",
        "",
        f"**Outlier.** {definitions['outlier']}",
        "",
        f"**Constant column.** {definitions['constant_column']}",
        "",
        f"**High cardinality.** {definitions['high_cardinality']}",
        "",
        f"**Severity.** {definitions['severity']}",
        "",
        f"**Row number.** {definitions['row_number']}",
        "",
        "### Quality checks",
        "",
    ]
    for name, description in checks.items():
        lines.append(f"- `{name}`: {description}")
    return "\n".join(lines)


def _evidence(evidence: dict[str, Any]) -> str:
    lines = ["**Evidence**", ""]
    if not evidence:
        lines.append("No structured evidence was recorded.")
        return "\n".join(lines)
    for key, value in evidence.items():
        label = key.replace("_", " ")
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            lines.append(f"- {label}:")
            lines.append("")
            lines.append(_dict_table(value))
            lines.append("")
        elif isinstance(value, dict):
            rendered = _token_text(value) if value else "none"
            lines.append(f"- {label}: {rendered}")
        else:
            lines.append(f"- {label}: {_fmt_key(key, value)}")
    return "\n".join(lines).rstrip()


def _kv_table(rows: list[tuple[str, Any]]) -> str:
    return _table(["Field", "Value"], [[label, value] for label, value in rows])


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "| " + " | ".join(md_cell(header) for header in headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = [
        "| " + " | ".join(md_cell(cell) for cell in row) + " |"
        for row in rows
    ]
    return "\n".join([head, rule, *body])


def _dict_table(rows: list[dict[str, Any]]) -> str:
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(str(key))
    return _table(
        [key.replace("_", " ") for key in keys],
        [[_fmt(row.get(key)) for key in keys] for row in rows],
    )


def md_cell(value: Any) -> str:
    """Escape a Markdown table cell."""
    text = "" if value is None else str(value)
    text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return text.replace("|", "\\|")


def _token_text(tokens: dict[str, Any]) -> str:
    if not tokens:
        return "none"
    return ", ".join(f"{key} ({_fmt(count)})" for key, count in tokens.items())


def _fmt_key(key: str, value: Any) -> str:
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return _fmt(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if key in _PERCENT_POINT_KEYS:
            return _percent_points(float(value))
        if key in _FRACTION_KEYS:
            return f"{_fmt(value)} ({float(value):.2%})"
    return _fmt(value)


def _percent_points(value: float) -> str:
    return f"{value:.2f}%"


def _fmt(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return _fmt_float(value)
    return str(value)


def _fmt_float(value: float) -> str:
    if value != 0 and (abs(value) >= 1e7 or abs(value) < 1e-4):
        return f"{value:.6g}"
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    if text in {"", "-"}:
        return "0.0"
    if "." not in text:
        text += ".0"
    return text


def _inline(value: str) -> str:
    return str(value).replace("`", "'")
