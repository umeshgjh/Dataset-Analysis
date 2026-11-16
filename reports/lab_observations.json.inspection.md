# Data Inspection Report

**Smart Data Inspector 1.0.0** inspected `lab_observations.json` at 2026-11-16T13:00:35Z.

Severities distinguish consistency problems (`error`) from issues that may still be legitimate (`warning`) and potential anomalies that are not evidence a value is wrong (`info`). Statistical outliers are never treated as confirmed errors. This report does not include an overall quality score and it does not change the source file.

| Field | Value |
| --- | --- |
| Rows | 8 |
| Columns | 6 |
| Extra duplicate rows | 0 |
| Findings | 0 (error: 0, warning: 0, info: 0) |

## Input File

| Field | Value |
| --- | --- |
| Path | `examples/lab_observations.json` |
| Absolute path | `/Users/umeshgjh/Projects/A*/Dataset-Analysis/examples/lab_observations.json` |
| Format | json |
| Size | 1210 bytes |
| Encoding | utf-8 |
| Python | 3.12.15 |
| pandas | 3.1.1 |
| NumPy | 2.5.5 |

## Dataset Overview

The table has 8 rows and 6 columns.

Column names, in file order: `subject`, `temperature_c`, `replicate`, `recorded_on`, `passed`, `method`.

## Column Types

Types are inferred from the non-missing values. `dominant_type` is the kind that covers the most values. `inferred_type` is `categorical` for short labels, including a code column whose integer-like tokens and letter-and-digit codes belong to one label set. It is `string` for free text, `mixed` when no kind is stable, and `unknown` when every value is missing.

| Column | Inferred type | Dominant type | Unique | Unexpected |
| --- | --- | --- | --- | --- |
| subject | categorical | string | 2 | 0 |
| temperature_c | float | float | 8 | 0 |
| replicate | integer | integer | 2 | 0 |
| recorded_on | datetime | datetime | 4 | 0 |
| passed | boolean | boolean | 2 | 0 |
| method | categorical | string | 2 | 0 |

### Classification notes

- `subject`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 4.5 characters, limit 40) and none contain a newline.
- `temperature_c`: Accepted as float because every non-missing value is a float.
- `replicate`: Accepted as integer because every non-missing value is an integer.
- `recorded_on`: Accepted as datetime because every non-missing value matches an unambiguous year-first date or timestamp.
- `passed`: Accepted as boolean because every non-missing value is a JSON boolean or one of true, false, yes, and no.
- `method`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 1.0 characters, limit 40) and none contain a newline.

## Missing-Value Analysis

A value is missing when it is JSON null, an absent JSON key, a non-standard JSON NaN, an empty or whitespace-only cell, or a configured missing token such as null, none, nan, or n/a (matched without regard to case or surrounding space). The number 0, the boolean false, and the text "0" or "false" are not missing unless those exact tokens are added to the configuration. The bare token "na" is not missing by default because it can be a real code.

| Column | Missing | Missing % | Non-missing | Missing tokens |
| --- | --- | --- | --- | --- |
| subject | 0 | 0.00% | 8 | none |
| temperature_c | 0 | 0.00% | 8 | none |
| replicate | 0 | 0.00% | 8 | none |
| recorded_on | 0 | 0.00% | 8 | none |
| passed | 0 | 0.00% | 8 | none |
| method | 0 | 0.00% | 8 | none |

## Duplicate Rows

An exact duplicate is a row that matches another row on every column. All missing representations match each other, including empty cells, configured missing tokens, JSON null, and a JSON key that is absent from one object. Non-missing values must also have the same Python type: true is not a duplicate of 1, and the string "1" is not a duplicate of the number 1. Text is compared exactly, so leading or trailing spaces are preserved. The duplicate-row count is the number of extra copies beyond the first occurrence of each duplicated row.

| Field | Value |
| --- | --- |
| Extra duplicate rows | 0 |
| Rows in duplicate groups | 0 |
| Duplicate groups | 0 |

## Numeric Summaries

Minimum, maximum, and mean use only values compatible with the accepted numeric type. Excluded cells are non-numeric values left out of those statistics. Markdown shows numbers to 6 decimal places; the JSON report keeps full precision.

| Column | Count | Minimum | Maximum | Mean | Excluded | Outlier check |
| --- | --- | --- | --- | --- | --- | --- |
| temperature_c | 8 | 20.1 | 21.2 | 20.75 | 0 | completed |
| replicate | 8 | 1 | 2 | 1.5 | 0 | completed |

## Categorical Summaries

The most frequent value is the first non-missing value that reaches the highest count. Ties keep the value that appears earliest in the file. The share is the count divided by non-missing values.

| Column | Unique values | Most frequent | Count | Share of non-missing |
| --- | --- | --- | --- | --- |
| subject | 2 | alpha | 4 | 50.00% |
| method | 2 | A | 4 | 50.00% |

## Data-Quality Findings

0 finding(s): 0 error, 0 warning, 0 info.

No data-quality findings were raised for the enabled checks. Descriptive sections above are still the inspection result.

## Inspection Configuration

These are the settings that produced this report.

| Field | Value |
| --- | --- |
| Missingness threshold | 0.2 |
| Outlier method | iqr |
| Outlier multiplier | 1.5 |
| Outlier minimum samples | 4 |
| High-cardinality threshold | 0.5 |
| Categorical maximum length | 40 |
| Dominance threshold | 0.8 |
| Enabled checks | missingness, duplicates, mixed_types, outliers, constant_columns, high_cardinality |
| Disabled checks | none |
| Missing tokens | #n/a, #na, <na>, n/a, nan, nat, none, null |

A column is flagged when its missing fraction is strictly greater than missingness_threshold.

A categorical column is flagged when its distinct-value ratio is greater than or equal to high_cardinality_threshold.

A numeric value is flagged when it is strictly outside the IQR fences.

## Definitions

**Duplicate row.** An exact duplicate is a row that matches another row on every column. All missing representations match each other, including empty cells, configured missing tokens, JSON null, and a JSON key that is absent from one object. Non-missing values must also have the same Python type: true is not a duplicate of 1, and the string "1" is not a duplicate of the number 1. Text is compared exactly, so leading or trailing spaces are preserved. The duplicate-row count is the number of extra copies beyond the first occurrence of each duplicated row.

**Missing value.** A value is missing when it is JSON null, an absent JSON key, a non-standard JSON NaN, an empty or whitespace-only cell, or a configured missing token such as null, none, nan, or n/a (matched without regard to case or surrounding space). The number 0, the boolean false, and the text "0" or "false" are not missing unless those exact tokens are added to the configuration. The bare token "na" is not missing by default because it can be a real code.

**Column type.** Column types are inferred from non-missing values, not from a dataframe dtype. A value is boolean when it is a JSON boolean or one of the words true, false, yes, and no. A value is an integer when it is a JSON integer, or text made of an optional sign and digits, without a leading zero. A value is a float when it is a JSON float or text that contains a decimal point or an exponent. Datetime values must be unambiguous year-first dates, YYYY-MM-DD or YYYY/MM/DD, with an optional time. Day-month and month-day dates are left as text so a locale is never guessed. The dominant type is the compatible type that covers the most values. Integer values are compatible with float. When integer and float cover the same values, integer wins unless a float value is actually present. Other ties prefer boolean, then datetime, then integer, then float, then string. If the dominant type covers at least the dominance threshold, that type is accepted. Otherwise the column is mixed. One exception keeps a short-token column categorical when integer-like values appear together with text codes that contain both letters and digits and those codes use at least two different alphabetic patterns (the letters that remain after digits and signs are removed). The integer-like tokens are labels in that code set: they are not listed as unexpected, and the column is not given a numeric mean. This exception does not apply when an integer or float type already meets the dominance threshold, and it does not apply when every letter-and-digit code shares one alphabetic pattern. An accepted string column is categorical when its median character length is within the configured label length and no value contains a newline; otherwise it is free text. An all-missing column is unknown. Numeric summaries and outlier checks are produced only after a column is accepted as integer or float.

**Outlier.** Potential numerical outliers use the Tukey IQR rule. Q1 and Q3 are the 25th and 75th percentiles with the linear method: position (n - 1) * p on the sorted finite numeric values. The fences are Q1 - k * IQR and Q3 + k * IQR, where k is the configured multiplier (default 1.5). A value is listed only when it is strictly outside the fences. Only finite values compatible with an accepted integer or float column are included. Outliers are statistical candidates for review, not confirmed data errors.

**Constant column.** A constant column has exactly one distinct non-missing value. Missing values do not count as that value. An all-missing column is not constant.

**High cardinality.** A categorical column is high cardinality when its distinct-value ratio (unique non-missing values divided by non-missing values) is greater than or equal to the configured threshold and the column has at least two distinct values. Constant columns are not flagged by this rule. Numeric identifiers stay numeric, so they are not flagged here; their unique counts are still reported. The finding records many distinct values. It is an observation about an identifier or another near-unique label, not a claim that the column is defective.

**Severity.** error: the column has no stable type, or at least 90% of its values are missing. warning: a quality issue is likely but may still be legitimate, such as duplicate rows, a constant field, moderate missingness, or a minority of values that do not match the dominant type. info: something to review that is not a confirmed error. Statistical outliers are potential anomalies. High cardinality is an observation that a column has many distinct values, often because it is an identifier.

**Row number.** Row numbers in findings are 1-based positions in the loaded table. They do not count a CSV header. Completely blank CSV lines are not rows.

### Quality checks

- `missingness`: Flag a column when its missing-value fraction exceeds the configured threshold.
- `duplicates`: Flag the dataset when any exact duplicate rows are present.
- `mixed_types`: Flag a column that contains values incompatible with its dominant type.
- `outliers`: Flag potential numerical outliers using the IQR rule. These are not confirmed errors.
- `constant_columns`: Flag a column with only one distinct non-missing value.
- `high_cardinality`: Flag a categorical column whose distinct-value ratio meets the configured threshold.
