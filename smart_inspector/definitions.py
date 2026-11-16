"""Wording shared by the Markdown and JSON reports.

Both formats read these strings so an explanation cannot drift between them.
"""

DUPLICATE_DEFINITION = (
    "An exact duplicate is a row that matches another row on every column. "
    "All missing representations match each other, including empty cells, "
    "configured missing tokens, JSON null, and a JSON key that is absent from one object. "
    'Non-missing values must also have the same Python type: true is not a duplicate of 1, '
    'and the string "1" is not a duplicate of the number 1. '
    "Text is compared exactly, so leading or trailing spaces are preserved. "
    "The duplicate-row count is the number of extra copies beyond the first occurrence "
    "of each duplicated row."
)

MISSING_DEFINITION = (
    "A value is missing when it is JSON null, an absent JSON key, a non-standard JSON NaN, "
    "an empty or whitespace-only cell, or a configured missing token such as null, none, nan, "
    "or n/a (matched without regard to case or surrounding space). "
    'The number 0, the boolean false, and the text "0" or "false" are not missing unless those '
    'exact tokens are added to the configuration. The bare token "na" is not missing by default '
    "because it can be a real code."
)

TYPE_DEFINITION = (
    "Column types are inferred from non-missing values, not from a dataframe dtype. "
    "A value is boolean when it is a JSON boolean or one of the words true, false, yes, and no. "
    "A value is an integer when it is a JSON integer, or text made of an optional sign and digits, "
    "without a leading zero. "
    "A value is a float when it is a JSON float or text that contains a decimal point or an exponent. "
    "Datetime values must be unambiguous year-first dates, YYYY-MM-DD or YYYY/MM/DD, with an optional time. "
    "Day-month and month-day dates are left as text so a locale is never guessed. "
    "The dominant type is the compatible type that covers the most values. "
    "Integer values are compatible with float. When integer and float cover the same values, "
    "integer wins unless a float value is actually present. Other ties prefer boolean, then datetime, "
    "then integer, then float, then string. "
    "If the dominant type covers at least the dominance threshold, that type is accepted. "
    "Otherwise the column is mixed. "
    "An accepted string column is categorical when its median character length is within the "
    "configured label length and no value contains a newline; otherwise it is free text. "
    "An all-missing column is unknown. "
    "Numeric summaries and outlier checks are produced only after a column is accepted as integer or float."
)

OUTLIER_DEFINITION = (
    "Potential numerical outliers use the Tukey IQR rule. "
    "Q1 and Q3 are the 25th and 75th percentiles with the linear method: "
    "position (n - 1) * p on the sorted finite numeric values. "
    "The fences are Q1 - k * IQR and Q3 + k * IQR, where k is the configured multiplier (default 1.5). "
    "A value is listed only when it is strictly outside the fences. "
    "Only finite values compatible with an accepted integer or float column are included. "
    "Outliers are statistical candidates for review, not confirmed data errors."
)

CONSTANT_DEFINITION = (
    "A constant column has exactly one distinct non-missing value. "
    "Missing values do not count as that value. An all-missing column is not constant."
)

HIGH_CARDINALITY_DEFINITION = (
    "A categorical column is high cardinality when its distinct-value ratio "
    "(unique non-missing values divided by non-missing values) is greater than or equal to "
    "the configured threshold and the column has at least two distinct values. "
    "Constant columns are not flagged by this rule. "
    "Numeric identifiers stay numeric, so they are not flagged here; their unique counts are still reported."
)

SEVERITY_DEFINITION = (
    "error: the column has no stable type, or at least 90% of its values are missing. "
    "warning: a quality issue is likely but may still be legitimate, such as duplicate rows, "
    "a constant field, moderate missingness, or a minority of values that do not match the dominant type. "
    "info: a potential anomaly to review. Statistical outliers and high-cardinality categories are info "
    "because they are not evidence that a value is wrong."
)

ROW_NUMBER_DEFINITION = (
    "Row numbers in findings are 1-based positions in the loaded table. "
    "They do not count a CSV header. Completely blank CSV lines are not rows."
)

MISSINGNESS_COMPARISON = (
    "A column is flagged when its missing fraction is strictly greater than missingness_threshold."
)

HIGH_CARDINALITY_COMPARISON = (
    "A categorical column is flagged when its distinct-value ratio is greater than or equal to "
    "high_cardinality_threshold."
)

OUTLIER_COMPARISON = "A numeric value is flagged when it is strictly outside the IQR fences."

CHECK_CATALOG = {
    "missingness": (
        "Flag a column when its missing-value fraction exceeds the configured threshold."
    ),
    "duplicates": "Flag the dataset when any exact duplicate rows are present.",
    "mixed_types": "Flag a column that contains values incompatible with its dominant type.",
    "outliers": (
        "Flag potential numerical outliers using the IQR rule. These are not confirmed errors."
    ),
    "constant_columns": "Flag a column with only one distinct non-missing value.",
    "high_cardinality": (
        "Flag a categorical column whose distinct-value ratio meets the configured threshold."
    ),
}
