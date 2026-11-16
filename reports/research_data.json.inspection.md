# Data Inspection Report

**Smart Data Inspector 1.0.0** inspected `research_data.json` at 2026-11-16T12:53:45Z.

Severities distinguish consistency problems (`error`) from issues that may still be legitimate (`warning`) and potential anomalies that are not evidence a value is wrong (`info`). Statistical outliers are never treated as confirmed errors. This report does not include an overall quality score and it does not change the source file.

| Field | Value |
| --- | --- |
| Rows | 4 |
| Columns | 5 |
| Extra duplicate rows | 1 |
| Findings | 6 (error: 0, warning: 3, info: 3) |

## Input File

| Field | Value |
| --- | --- |
| Path | `examples/research_data.json` |
| Absolute path | `/Users/umeshgjh/Projects/A*/Dataset-Analysis/examples/research_data.json` |
| Format | json |
| Size | 432 bytes |
| Encoding | utf-8 |
| Python | 3.12.15 |
| pandas | 3.1.1 |
| NumPy | 2.5.5 |

## Dataset Overview

The table has 4 rows and 5 columns.

Column names, in file order: `record_id`, `measurement`, `enrolled`, `retries`, `note`.

## Column Types

Types are inferred from the non-missing values. `dominant_type` is the kind that covers the most values. `inferred_type` is `categorical` for short labels, including a code column whose integer-like tokens and letter-and-digit codes belong to one label set. It is `string` for free text, `mixed` when no kind is stable, and `unknown` when every value is missing.

| Column | Inferred type | Dominant type | Unique | Unexpected |
| --- | --- | --- | --- | --- |
| record_id | categorical | string | 3 | 0 |
| measurement | integer | integer | 3 | 0 |
| enrolled | boolean | boolean | 2 | 0 |
| retries | integer | integer | 2 | 0 |
| note | categorical | string | 1 | 0 |

### Classification notes

- `record_id`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 2.0 characters, limit 40) and none contain a newline.
- `measurement`: Accepted as integer because every non-missing value is an integer.
- `enrolled`: Accepted as boolean because every non-missing value is a JSON boolean or one of true, false, yes, and no.
- `retries`: Accepted as integer because every non-missing value is an integer.
- `note`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 2.0 characters, limit 40) and none contain a newline.

## Missing-Value Analysis

A value is missing when it is JSON null, an absent JSON key, a non-standard JSON NaN, an empty or whitespace-only cell, or a configured missing token such as null, none, nan, or n/a (matched without regard to case or surrounding space). The number 0, the boolean false, and the text "0" or "false" are not missing unless those exact tokens are added to the configuration. The bare token "na" is not missing by default because it can be a real code.

| Column | Missing | Missing % | Non-missing | Missing tokens |
| --- | --- | --- | --- | --- |
| record_id | 0 | 0.00% | 4 | none |
| measurement | 0 | 0.00% | 4 | none |
| enrolled | 0 | 0.00% | 4 | none |
| retries | 0 | 0.00% | 4 | none |
| note | 2 | 50.00% | 2 | <absent> (1), <null> (1) |

## Duplicate Rows

An exact duplicate is a row that matches another row on every column. All missing representations match each other, including empty cells, configured missing tokens, JSON null, and a JSON key that is absent from one object. Non-missing values must also have the same Python type: true is not a duplicate of 1, and the string "1" is not a duplicate of the number 1. Text is compared exactly, so leading or trailing spaces are preserved. The duplicate-row count is the number of extra copies beyond the first occurrence of each duplicated row.

| Field | Value |
| --- | --- |
| Extra duplicate rows | 1 |
| Rows in duplicate groups | 2 |
| Duplicate groups | 1 |

## Numeric Summaries

Minimum, maximum, and mean use only values compatible with the accepted numeric type. Excluded cells are non-numeric values left out of those statistics. Markdown shows numbers to 6 decimal places; the JSON report keeps full precision.

| Column | Count | Minimum | Maximum | Mean | Excluded | Outlier check |
| --- | --- | --- | --- | --- | --- | --- |
| measurement | 4 | 1 | 100 | 26.0 | 0 | completed |
| retries | 4 | 0 | 1 | 0.25 | 0 | completed |

## Categorical Summaries

The most frequent value is the first non-missing value that reaches the highest count. Ties keep the value that appears earliest in the file. The share is the count divided by non-missing values.

| Column | Unique values | Most frequent | Count | Share of non-missing |
| --- | --- | --- | --- | --- |
| record_id | 3 | R1 | 2 | 50.00% |
| note | 1 | ok | 2 | 100.00% |

## Data-Quality Findings

6 finding(s): 0 error, 3 warning, 3 info.

### 1. High missingness in column 'note'

| Field | Value |
| --- | --- |
| Rule | missingness |
| Severity | warning |
| Scope | column |
| Affected column or dataset | note |
| Affected records | 2 |

**Evidence**

- missing count: 2
- non missing count: 2
- row count: 4
- missing fraction: 0.5 (50.00%)
- missing percentage: 50.00%
- threshold: 0.2 (20.00%)
- missing tokens: <absent> (1), <null> (1)

**Why this was flagged**

2 of 4 values (50.00%) in column 'note' are missing, which exceeds the configured threshold of 20.00% of rows. The column still has some observed values, but this amount of missingness can bias summaries and group comparisons.

**Suggested action**

Confirm whether the missing values are expected. If the column is unused, exclude it from analysis. If the values should be present, check the export or the collection process. Do not impute until the reason is understood.

### 2. Duplicate rows detected

| Field | Value |
| --- | --- |
| Rule | duplicates |
| Severity | warning |
| Scope | dataset |
| Affected column or dataset | dataset |
| Affected records | 1 |

**Evidence**

- extra duplicate rows: 1
- rows in duplicate groups: 2
- duplicate group count: 1
- row count: 4

**Why this was flagged**

1 extra row is an exact copy of an earlier row (2 rows sit in 1 duplicated group). Exact means every column matches, with all missing representations treated as equal and with text and types compared exactly. Duplicates can be legitimate repeated measurements or an export problem. This finding does not by itself prove the rows are wrong.

**Suggested action**

Review the duplicated rows with the data owner. Keep them if they are legitimate repeated observations. If they come from a join or an export, drop the extra copies before analysis. This tool does not delete rows.

### 3. Potential numerical outliers in column 'measurement'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | measurement |
| Affected records | 1 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 4
- q1: 1.0
- q3: 26.5
- iqr: 25.5
- lower bound: -37.25
- upper bound: 64.75
- outlier count: 1
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 3 | 100 | 100.0 | 35.25 | false |

- sample limit: 10
- sample truncated: false
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

1 numeric value in column 'measurement' falls strictly outside the Tukey fences [-37.25, 64.75] (Q1=1, Q3=26.5, IQR=25.5, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 4. Potential numerical outliers in column 'retries'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | retries |
| Affected records | 1 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 4
- q1: 0.0
- q3: 0.25
- iqr: 0.25
- lower bound: -0.375
- upper bound: 0.625
- outlier count: 1
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 2 | 1 | 1.0 | 0.375 | false |

- sample limit: 10
- sample truncated: false
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

1 numeric value in column 'retries' falls strictly outside the Tukey fences [-0.375, 0.625] (Q1=0, Q3=0.25, IQR=0.25, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 5. Constant column 'note'

| Field | Value |
| --- | --- |
| Rule | constant_columns |
| Severity | warning |
| Scope | column |
| Affected column or dataset | note |
| Affected records | 2 |

**Evidence**

- constant value: ok
- value truncated: false
- non missing count: 2
- missing count: 2
- unique non missing: 1

**Why this was flagged**

Column 'note' has a single distinct non-missing value ('ok'). 2 observed rows share it and 2 rows are missing. A constant column does not distinguish records. It can be intentional, for example after a filter, or a sign that the export filled one value.

**Suggested action**

If the column is intentionally uniform, for example because a filter kept one site, you can ignore this finding. Otherwise it will not help distinguish records and may indicate a failed export.

### 6. High cardinality in column 'record_id'

| Field | Value |
| --- | --- |
| Rule | high_cardinality |
| Severity | info |
| Scope | column |
| Affected column or dataset | record_id |
| Affected records | 3 |

**Evidence**

- unique count: 3
- non missing count: 4
- distinct ratio: 0.75 (75.00%)
- threshold: 0.5 (50.00%)
- median value length: 2.0
- categorical max length: 40
- affected records meaning: distinct non-missing values

**Why this was flagged**

Column 'record_id' is categorical and has 3 distinct values out of 4 observed values (distinct-value ratio 0.75), which is at or above the threshold of 0.50. Affected records here means the number of distinct values, not a count of bad rows. This is an observation about cardinality: the column may be an identifier or another near-unique label, and that pattern is often legitimate and useful. It is not evidence that the values are incorrect. Small columns can cross the threshold with only a few distinct labels.

**Suggested action**

Treat this as an observation about distinctness, not as a defect. The column may be an identifier or another near-unique label, which is often legitimate and useful. If it will be used as a category in a grouped analysis, plan for the number of distinct values.

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
