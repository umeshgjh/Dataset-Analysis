# Data Inspection Report

**Smart Data Inspector 1.0.0** inspected `corrupted_observations.csv` at 2026-11-16T13:00:37Z.

Severities distinguish consistency problems (`error`) from issues that may still be legitimate (`warning`) and potential anomalies that are not evidence a value is wrong (`info`). Statistical outliers are never treated as confirmed errors. This report does not include an overall quality score and it does not change the source file.

| Field | Value |
| --- | --- |
| Rows | 12 |
| Columns | 7 |
| Extra duplicate rows | 1 |
| Findings | 7 (error: 1, warning: 4, info: 2) |

## Input File

| Field | Value |
| --- | --- |
| Path | `examples/corrupted_observations.csv` |
| Absolute path | `<redacted local absolute path>` |
| Format | csv |
| Size | 335 bytes |
| Encoding | utf-8 |
| Python | 3.12.15 |
| pandas | 3.1.1 |
| NumPy | 2.5.5 |

## Dataset Overview

The table has 12 rows and 7 columns.

Column names, in file order: `sample_id`, `site`, `measurement`, `score`, `batch`, `group_code`, `notes`.

## Column Types

Types are inferred from the non-missing values. `dominant_type` is the kind that covers the most values. `inferred_type` is `categorical` for short labels, including a code column whose integer-like tokens and letter-and-digit codes belong to one label set. It is `string` for free text, `mixed` when no kind is stable, and `unknown` when every value is missing.

| Column | Inferred type | Dominant type | Unique | Unexpected |
| --- | --- | --- | --- | --- |
| sample_id | categorical | string | 11 | 0 |
| site | categorical | string | 1 | 0 |
| measurement | integer | integer | 10 | 0 |
| score | integer | integer | 6 | 1 |
| batch | mixed | integer | 5 | 3 |
| group_code | categorical | integer | 5 | 0 |
| notes | categorical | string | 2 | 0 |

### Classification notes

- `sample_id`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 3.0 characters, limit 40) and none contain a newline.
- `site`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 5.0 characters, limit 40) and none contain a newline.
- `measurement`: Accepted as integer because every non-missing value is an integer.
- `score`: Accepted as integer because that type covers 11 of 12 non-missing values (91.67%), which meets the dominance threshold of 80%. 1 non-missing value does not match integer and is reported as unexpected.
- `batch`: Classified as mixed because the dominant type integer covers 9 of 12 non-missing values (75.00%), below the dominance threshold of 80%. Unexpected values are listed separately. Numeric summaries are omitted for mixed columns so a mean is not reported for an unstable type.
- `group_code`: Classified as categorical because the values are short codes rather than measurements. 7 non-missing values are integer-like and 5 are text. The letter-and-digit codes use 2 different alphabetic patterns, including 'mm2', '-42m'. Those patterns are different, so the integer-like tokens stay in the same label set. They are not listed as unexpected, and numeric summaries are omitted so a mean is not reported for codes. The closest single kind is integer, covering 7 of 12 non-missing values (58.33%), below the dominance threshold of 80%. The column is categorical rather than mixed because the two forms belong to one code set. Median label length is 1.0 characters, within the limit of 40.
- `notes`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 3.5 characters, limit 40) and none contain a newline.

## Missing-Value Analysis

A value is missing when it is JSON null, an absent JSON key, a non-standard JSON NaN, an empty or whitespace-only cell, or a configured missing token such as null, none, nan, or n/a (matched without regard to case or surrounding space). The number 0, the boolean false, and the text "0" or "false" are not missing unless those exact tokens are added to the configuration. The bare token "na" is not missing by default because it can be a real code.

| Column | Missing | Missing % | Non-missing | Missing tokens |
| --- | --- | --- | --- | --- |
| sample_id | 0 | 0.00% | 12 | none |
| site | 0 | 0.00% | 12 | none |
| measurement | 0 | 0.00% | 12 | none |
| score | 0 | 0.00% | 12 | none |
| batch | 0 | 0.00% | 12 | none |
| group_code | 0 | 0.00% | 12 | none |
| notes | 6 | 50.00% | 6 | <empty> (6) |

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
| measurement | 12 | 1 | 100 | 12.583333 | 0 | completed |
| score | 11 | 9 | 13 | 10.818182 | 1 | completed |

## Categorical Summaries

The most frequent value is the first non-missing value that reaches the highest count. Ties keep the value that appears earliest in the file. The share is the count divided by non-missing values.

| Column | Unique values | Most frequent | Count | Share of non-missing |
| --- | --- | --- | --- | --- |
| sample_id | 11 | S01 | 2 | 16.67% |
| site | 1 | north | 12 | 100.00% |
| group_code | 5 | 1 | 3 | 25.00% |
| notes | 2 | ok | 3 | 50.00% |

## Data-Quality Findings

7 finding(s): 1 error, 4 warning, 2 info.

### 1. High missingness in column 'notes'

| Field | Value |
| --- | --- |
| Rule | missingness |
| Severity | warning |
| Scope | column |
| Affected column or dataset | notes |
| Affected records | 6 |

**Evidence**

- missing count: 6
- non missing count: 6
- row count: 12
- missing fraction: 0.5 (50.00%)
- missing percentage: 50.00%
- threshold: 0.2 (20.00%)
- missing tokens: <empty> (6)

**Why this was flagged**

6 of 12 values (50.00%) in column 'notes' are missing, which exceeds the configured threshold of 20.00% of rows. The column still has some observed values, but this amount of missingness can bias summaries and group comparisons.

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
- row count: 12

**Why this was flagged**

1 extra row is an exact copy of an earlier row (2 rows sit in 1 duplicated group). Exact means every column matches, with all missing representations treated as equal and with text and types compared exactly. Duplicates can be legitimate repeated measurements or an export problem. This finding does not by itself prove the rows are wrong.

**Suggested action**

Review the duplicated rows with the data owner. Keep them if they are legitimate repeated observations. If they come from a join or an export, drop the extra copies before analysis. This tool does not delete rows.

### 3. Inconsistent values in column 'score'

| Field | Value |
| --- | --- |
| Rule | mixed_types |
| Severity | warning |
| Scope | column |
| Affected column or dataset | score |
| Affected records | 1 |

**Evidence**

- inferred type: integer
- dominant type: integer
- unexpected count: 1
- unexpected distinct count: 1
- non missing count: 12
- unexpected fraction: 0.083333 (8.33%)
- dominance threshold: 0.8 (80.00%)
- type counts: boolean (0), integer (11), float (0), datetime (0), string (1)
- sample values:

| value | kind | count | first row | truncated |
| --- | --- | --- | --- | --- |
| bad | string | 1 | 7 | false |

- sample limit: 10
- sample truncated: false

**Why this was flagged**

The column was accepted as integer because integer is the dominant type, but 1 of 12 non-missing values (8.33%) does not match it. Those values were not converted.

**Suggested action**

Inspect the unexpected values in the evidence. Correct formatting errors, or split the column if it intentionally mixes different kinds of values. Do not convert the column automatically; that would hide the inconsistent records.

### 4. Inconsistent values in column 'batch'

| Field | Value |
| --- | --- |
| Rule | mixed_types |
| Severity | error |
| Scope | column |
| Affected column or dataset | batch |
| Affected records | 3 |

**Evidence**

- inferred type: mixed
- dominant type: integer
- unexpected count: 3
- unexpected distinct count: 2
- non missing count: 12
- unexpected fraction: 0.25 (25.00%)
- dominance threshold: 0.8 (80.00%)
- type counts: boolean (0), integer (9), float (0), datetime (0), string (3)
- sample values:

| value | kind | count | first row | truncated |
| --- | --- | --- | --- | --- |
| abc | string | 2 | 4 | false |
| x | string | 1 | 11 | false |

- sample limit: 10
- sample truncated: false

**Why this was flagged**

No type reached the dominance threshold of 80%. The closest type is integer, and 3 of 12 non-missing values (25.00%) do not match it. The column is therefore mixed rather than coerced.

**Suggested action**

Inspect the unexpected values in the evidence. Correct formatting errors, or split the column if it intentionally mixes different kinds of values. Do not convert the column automatically; that would hide the inconsistent records.

### 5. Potential numerical outliers in column 'measurement'

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
- sample size: 12
- q1: 2.75
- q3: 7.25
- iqr: 4.5
- lower bound: -4.0
- upper bound: 14.0
- outlier count: 1
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 10 | 100 | 100.0 | 86.0 | false |

- sample limit: 10
- sample truncated: false
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

1 numeric value in column 'measurement' falls strictly outside the Tukey fences [-4, 14] (Q1=2.75, Q3=7.25, IQR=4.5, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 6. Constant column 'site'

| Field | Value |
| --- | --- |
| Rule | constant_columns |
| Severity | warning |
| Scope | column |
| Affected column or dataset | site |
| Affected records | 12 |

**Evidence**

- constant value: north
- value truncated: false
- non missing count: 12
- missing count: 0
- unique non missing: 1

**Why this was flagged**

Column 'site' has a single distinct non-missing value ('north'). 12 observed rows share it and 0 rows are missing. A constant column does not distinguish records. It can be intentional, for example after a filter, or a sign that the export filled one value.

**Suggested action**

If the column is intentionally uniform, for example because a filter kept one site, you can ignore this finding. Otherwise it will not help distinguish records and may indicate a failed export.

### 7. High cardinality in column 'sample_id'

| Field | Value |
| --- | --- |
| Rule | high_cardinality |
| Severity | info |
| Scope | column |
| Affected column or dataset | sample_id |
| Affected records | 11 |

**Evidence**

- unique count: 11
- non missing count: 12
- distinct ratio: 0.916667 (91.67%)
- threshold: 0.5 (50.00%)
- median value length: 3.0
- categorical max length: 40
- affected records meaning: distinct non-missing values

**Why this was flagged**

Column 'sample_id' is categorical and has 11 distinct values out of 12 observed values (distinct-value ratio 0.92), which is at or above the threshold of 0.50. Affected records here means the number of distinct values, not a count of bad rows. This is an observation about cardinality: the column may be an identifier or another near-unique label, and that pattern is often legitimate and useful. It is not evidence that the values are incorrect. Small columns can cross the threshold with only a few distinct labels.

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
