# Data Inspection Report

**Smart Data Inspector 1.0.0** inspected `materials_piezoelectric_properties.csv` at 2026-11-16T13:00:35Z.

Severities distinguish consistency problems (`error`) from issues that may still be legitimate (`warning`) and potential anomalies that are not evidence a value is wrong (`info`). Statistical outliers are never treated as confirmed errors. This report does not include an overall quality score and it does not change the source file.

| Field | Value |
| --- | --- |
| Rows | 3322 |
| Columns | 15 |
| Extra duplicate rows | 0 |
| Findings | 10 (error: 0, warning: 0, info: 10) |

## Input File

| Field | Value |
| --- | --- |
| Path | `datasets/materials_piezoelectric_properties.csv` |
| Absolute path | `<redacted local absolute path>` |
| Format | csv |
| Size | 520849 bytes |
| Encoding | utf-8 |
| Python | 3.12.15 |
| pandas | 3.1.1 |
| NumPy | 2.5.5 |

## Dataset Overview

The table has 3322 rows and 15 columns.

Column names, in file order: `material_id`, `formula_pretty`, `e_longitudinal_max`, `e_abs_max`, `band_gap`, `crystal_system`, `point_group`, `is_metal`, `formation_energy_per_atom`, `energy_above_hull`, `density`, `is_stable`, `theoretical`, `num_atoms_in_cell`, `num_distinct_elements`.

## Column Types

Types are inferred from the non-missing values. `dominant_type` is the kind that covers the most values. `inferred_type` is `categorical` for short labels, including a code column whose integer-like tokens and letter-and-digit codes belong to one label set. It is `string` for free text, `mixed` when no kind is stable, and `unknown` when every value is missing.

| Column | Inferred type | Dominant type | Unique | Unexpected |
| --- | --- | --- | --- | --- |
| material_id | categorical | string | 3322 | 0 |
| formula_pretty | categorical | string | 2817 | 0 |
| e_longitudinal_max | float | float | 3231 | 0 |
| e_abs_max | float | float | 3295 | 0 |
| band_gap | float | float | 3205 | 0 |
| crystal_system | categorical | string | 7 | 0 |
| point_group | categorical | string | 21 | 0 |
| is_metal | boolean | boolean | 2 | 0 |
| formation_energy_per_atom | float | float | 3315 | 0 |
| energy_above_hull | float | float | 2050 | 0 |
| density | float | float | 3322 | 0 |
| is_stable | boolean | boolean | 2 | 0 |
| theoretical | boolean | boolean | 2 | 0 |
| num_atoms_in_cell | integer | integer | 69 | 0 |
| num_distinct_elements | integer | integer | 6 | 0 |

### Classification notes

- `material_id`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 11.0 characters, limit 40) and none contain a newline.
- `formula_pretty`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 7.0 characters, limit 40) and none contain a newline.
- `e_longitudinal_max`: Accepted as float because every non-missing value is a float.
- `e_abs_max`: Accepted as float because every non-missing value is a float.
- `band_gap`: Accepted as float because every non-missing value is a float.
- `crystal_system`: Accepted as string because every non-missing value is text. Classified as categorical because the values are short labels (median length 10.0 characters, limit 40) and none contain a newline.
- `point_group`: Classified as categorical because the values are short codes rather than measurements. 1313 non-missing values are integer-like and 2009 are text. The letter-and-digit codes use 2 different alphabetic patterns, including 'mm2', '-42m', '-43m'. Those patterns are different, so the integer-like tokens stay in the same label set. They are not listed as unexpected, and numeric summaries are omitted so a mean is not reported for codes. The closest single kind is string, covering 2009 of 3322 non-missing values (60.48%), below the dominance threshold of 80%. The column is categorical rather than mixed because the two forms belong to one code set. Median label length is 3.0 characters, within the limit of 40.
- `is_metal`: Accepted as boolean because every non-missing value is a JSON boolean or one of true, false, yes, and no.
- `formation_energy_per_atom`: Accepted as float because every non-missing value is a float.
- `energy_above_hull`: Accepted as float because every non-missing value is a float.
- `density`: Accepted as float because every non-missing value is a float.
- `is_stable`: Accepted as boolean because every non-missing value is a JSON boolean or one of true, false, yes, and no.
- `theoretical`: Accepted as boolean because every non-missing value is a JSON boolean or one of true, false, yes, and no.
- `num_atoms_in_cell`: Accepted as integer because every non-missing value is an integer.
- `num_distinct_elements`: Accepted as integer because every non-missing value is an integer.

## Missing-Value Analysis

A value is missing when it is JSON null, an absent JSON key, a non-standard JSON NaN, an empty or whitespace-only cell, or a configured missing token such as null, none, nan, or n/a (matched without regard to case or surrounding space). The number 0, the boolean false, and the text "0" or "false" are not missing unless those exact tokens are added to the configuration. The bare token "na" is not missing by default because it can be a real code.

| Column | Missing | Missing % | Non-missing | Missing tokens |
| --- | --- | --- | --- | --- |
| material_id | 0 | 0.00% | 3322 | none |
| formula_pretty | 0 | 0.00% | 3322 | none |
| e_longitudinal_max | 0 | 0.00% | 3322 | none |
| e_abs_max | 0 | 0.00% | 3322 | none |
| band_gap | 6 | 0.18% | 3316 | <empty> (6) |
| crystal_system | 0 | 0.00% | 3322 | none |
| point_group | 0 | 0.00% | 3322 | none |
| is_metal | 6 | 0.18% | 3316 | <empty> (6) |
| formation_energy_per_atom | 6 | 0.18% | 3316 | <empty> (6) |
| energy_above_hull | 6 | 0.18% | 3316 | <empty> (6) |
| density | 0 | 0.00% | 3322 | none |
| is_stable | 5 | 0.15% | 3317 | <empty> (5) |
| theoretical | 5 | 0.15% | 3317 | <empty> (5) |
| num_atoms_in_cell | 0 | 0.00% | 3322 | none |
| num_distinct_elements | 0 | 0.00% | 3322 | none |

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
| e_longitudinal_max | 3322 | 0.0 | 91.577946 | 0.820654 | 0 | completed |
| e_abs_max | 3322 | 0.0 | 119.03583 | 0.835579 | 0 | completed |
| band_gap | 3316 | 0.0 | 8.3751 | 2.479559 | 0 | completed |
| formation_energy_per_atom | 3316 | -4.488967 | 4.688205 | -1.727033 | 0 | completed |
| energy_above_hull | 3316 | 0.0 | 4.882445 | 0.045447 | 0 | completed |
| density | 3322 | 0.212291 | 13.160492 | 4.10656 | 0 | completed |
| num_atoms_in_cell | 3322 | 2 | 288 | 22.196869 | 0 | completed |
| num_distinct_elements | 3322 | 1 | 6 | 3.300421 | 0 | completed |

## Categorical Summaries

The most frequent value is the first non-missing value that reaches the highest count. Ties keep the value that appears earliest in the file. The share is the count divided by non-missing values.

| Column | Unique values | Most frequent | Count | Share of non-missing |
| --- | --- | --- | --- | --- |
| material_id | 3322 | mp-aaaaaywi | 1 | 0.03% |
| formula_pretty | 2817 | SiO2 | 44 | 1.32% |
| crystal_system | 7 | Orthorhombic | 876 | 26.37% |
| point_group | 21 | mm2 | 641 | 19.30% |

## Data-Quality Findings

10 finding(s): 0 error, 0 warning, 10 info.

### 1. Potential numerical outliers in column 'e_longitudinal_max'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | e_longitudinal_max |
| Affected records | 273 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3322
- q1: 0.124283
- q3: 0.754926
- iqr: 0.630644
- lower bound: -0.821683
- upper bound: 1.700892
- outlier count: 273
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 346 | 91.57794588219846 | 91.577946 | 89.877054 | false |
| 2499 | 90.59728002370431 | 90.59728 | 88.896388 | false |
| 592 | 58.9556987164464 | 58.955699 | 57.254807 | false |
| 831 | 52.552513301398065 | 52.552513 | 50.851622 | false |
| 2389 | 42.04995229956169 | 42.049952 | 40.349061 | false |
| 1470 | 36.95328397788007 | 36.953284 | 35.252392 | false |
| 2204 | 28.17351358305 | 28.173514 | 26.472622 | false |
| 2129 | 27.41792103375632 | 27.417921 | 25.717029 | false |
| 1467 | 26.733859776711835 | 26.73386 | 25.032968 | false |
| 1459 | 17.727681852578943 | 17.727682 | 16.02679 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

273 numeric values in column 'e_longitudinal_max' fall strictly outside the Tukey fences [-0.821683, 1.70089] (Q1=0.124283, Q3=0.754926, IQR=0.630644, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 2. Potential numerical outliers in column 'e_abs_max'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | e_abs_max |
| Affected records | 307 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3322
- q1: 0.145245
- q3: 0.73894
- iqr: 0.593695
- lower bound: -0.745298
- upper bound: 1.629483
- outlier count: 307
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 346 | 119.03583000000002 | 119.03583 | 117.406347 | false |
| 592 | 74.9909953951448 | 74.990995 | 73.361513 | false |
| 2499 | 68.9846155990392 | 68.984616 | 67.355133 | false |
| 831 | 52.18405330984899 | 52.184053 | 50.554571 | false |
| 671 | 32.504329999999996 | 32.50433 | 30.874847 | false |
| 2204 | 31.61500999999999 | 31.61501 | 29.985527 | false |
| 1470 | 31.474146689858895 | 31.474147 | 29.844664 | false |
| 2389 | 29.225641007735113 | 29.225641 | 27.596158 | false |
| 1881 | 22.348356684815236 | 22.348357 | 20.718874 | false |
| 2129 | 21.09989018941944 | 21.09989 | 19.470408 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

307 numeric values in column 'e_abs_max' fall strictly outside the Tukey fences [-0.745298, 1.62948] (Q1=0.145245, Q3=0.73894, IQR=0.593695, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 3. Potential numerical outliers in column 'band_gap'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | band_gap |
| Affected records | 13 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3316
- q1: 1.163
- q3: 3.6265
- iqr: 2.4635
- lower bound: -2.53225
- upper bound: 7.32175
- outlier count: 13
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 2335 | 8.3751 | 8.3751 | 1.05335 | false |
| 1629 | 8.319600000000001 | 8.3196 | 0.99785 | false |
| 2156 | 8.246 | 8.246 | 0.92425 | false |
| 1413 | 8.0901 | 8.0901 | 0.76835 | false |
| 3020 | 7.9632 | 7.9632 | 0.64145 | false |
| 1704 | 7.915100000000001 | 7.9151 | 0.59335 | false |
| 2872 | 7.9037999999999995 | 7.9038 | 0.58205 | false |
| 3019 | 7.729800000000001 | 7.7298 | 0.40805 | false |
| 3018 | 7.6375 | 7.6375 | 0.31575 | false |
| 1758 | 7.569555168170043 | 7.569555 | 0.247805 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

13 numeric values in column 'band_gap' fall strictly outside the Tukey fences [-2.53225, 7.32175] (Q1=1.163, Q3=3.6265, IQR=2.4635, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 4. Potential numerical outliers in column 'formation_energy_per_atom'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | formation_energy_per_atom |
| Affected records | 2 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3316
- q1: -2.523458
- q3: -0.898324
- iqr: 1.625134
- lower bound: -4.96116
- upper bound: 1.539377
- outlier count: 2
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 2180 | 4.68820494375 | 4.688205 | 3.148827 | false |
| 2487 | 2.9486191449999994 | 2.948619 | 1.409242 | false |

- sample limit: 10
- sample truncated: false
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

2 numeric values in column 'formation_energy_per_atom' fall strictly outside the Tukey fences [-4.96116, 1.53938] (Q1=-2.52346, Q3=-0.898324, IQR=1.62513, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 5. Potential numerical outliers in column 'energy_above_hull'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | energy_above_hull |
| Affected records | 213 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3316
- q1: 0.0
- q3: 0.055436
- iqr: 0.055436
- lower bound: -0.083154
- upper bound: 0.13859
- outlier count: 213
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 2487 | 4.882445304 | 4.882445 | 4.743856 | false |
| 2180 | 4.68820494375 | 4.688205 | 4.549615 | false |
| 2484 | 3.4995940388750038 | 3.499594 | 3.361004 | false |
| 1748 | 1.4680567887499993 | 1.468057 | 1.329467 | false |
| 827 | 1.2521901337083357 | 1.25219 | 1.113601 | false |
| 2482 | 1.2398420583695602 | 1.239842 | 1.101253 | false |
| 2183 | 1.0040639209722206 | 1.004064 | 0.865474 | false |
| 1914 | 0.9941056325000002 | 0.994106 | 0.855516 | false |
| 48 | 0.853623748844611 | 0.853624 | 0.715034 | false |
| 924 | 0.8178256637499999 | 0.817826 | 0.679236 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

213 numeric values in column 'energy_above_hull' fall strictly outside the Tukey fences [-0.0831537, 0.13859] (Q1=0, Q3=0.0554358, IQR=0.0554358, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 6. Potential numerical outliers in column 'density'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | density |
| Affected records | 105 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3322
- q1: 2.814465
- q3: 5.04347
- iqr: 2.229005
- lower bound: -0.529042
- upper bound: 8.386977
- outlier count: 105
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 169 | 13.160491904380963 | 13.160492 | 4.773515 | false |
| 2795 | 12.974894682567243 | 12.974895 | 4.587918 | false |
| 772 | 12.503003576418914 | 12.503004 | 4.116027 | false |
| 773 | 12.501573461046508 | 12.501573 | 4.114597 | false |
| 2914 | 12.217438099750321 | 12.217438 | 3.830462 | false |
| 2927 | 12.145831810975574 | 12.145832 | 3.758855 | false |
| 1339 | 11.428092384396551 | 11.428092 | 3.041116 | false |
| 1335 | 11.414465768731445 | 11.414466 | 3.027489 | false |
| 1353 | 11.288528881415491 | 11.288529 | 2.901552 | false |
| 1337 | 11.279319440701425 | 11.279319 | 2.892343 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

105 numeric values in column 'density' fall strictly outside the Tukey fences [-0.529042, 8.38698] (Q1=2.81446, Q3=5.04347, IQR=2.229, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 7. Potential numerical outliers in column 'num_atoms_in_cell'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | num_atoms_in_cell |
| Affected records | 132 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3322
- q1: 12.0
- q3: 28.0
- iqr: 16.0
- lower bound: -12.0
- upper bound: 52.0
- outlier count: 132
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 1655 | 288 | 288.0 | 236.0 | false |
| 886 | 144 | 144.0 | 92.0 | false |
| 887 | 144 | 144.0 | 92.0 | false |
| 1656 | 144 | 144.0 | 92.0 | false |
| 1368 | 120 | 120.0 | 68.0 | false |
| 2639 | 108 | 108.0 | 56.0 | false |
| 1672 | 104 | 104.0 | 52.0 | false |
| 1699 | 104 | 104.0 | 52.0 | false |
| 1800 | 99 | 99.0 | 47.0 | false |
| 351 | 96 | 96.0 | 44.0 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

132 numeric values in column 'num_atoms_in_cell' fall strictly outside the Tukey fences [-12, 52] (Q1=12, Q3=28, IQR=16, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 8. Potential numerical outliers in column 'num_distinct_elements'

| Field | Value |
| --- | --- |
| Rule | outliers |
| Severity | info |
| Scope | column |
| Affected column or dataset | num_distinct_elements |
| Affected records | 23 |

**Evidence**

- method: iqr
- multiplier: 1.5
- sample size: 3322
- q1: 3.0
- q3: 4.0
- iqr: 1.0
- lower bound: 1.5
- upper bound: 5.5
- outlier count: 23
- sample values:

| row | value | numeric value | distance outside fence | truncated |
| --- | --- | --- | --- | --- |
| 71 | 6 | 6.0 | 0.5 | false |
| 72 | 6 | 6.0 | 0.5 | false |
| 73 | 6 | 6.0 | 0.5 | false |
| 74 | 6 | 6.0 | 0.5 | false |
| 75 | 6 | 6.0 | 0.5 | false |
| 217 | 1 | 1.0 | 0.5 | false |
| 775 | 6 | 6.0 | 0.5 | false |
| 962 | 6 | 6.0 | 0.5 | false |
| 1748 | 1 | 1.0 | 0.5 | false |
| 1784 | 1 | 1.0 | 0.5 | false |

- sample limit: 10
- sample truncated: true
- note: Values outside the fences are potential anomalies, not confirmed data errors.

**Why this was flagged**

23 numeric values in column 'num_distinct_elements' fall strictly outside the Tukey fences [1.5, 5.5] (Q1=3, Q3=4, IQR=1, multiplier=1.5). These are potential outliers, not confirmed data errors. A real extreme measurement can fall outside the fences, and the fences can also be tight when the interquartile range is small.

**Suggested action**

Review the listed values in context. A statistical outlier can be a valid extreme measurement. Do not remove or winsorize these values unless you have a domain reason to treat them as errors.

### 9. High cardinality in column 'material_id'

| Field | Value |
| --- | --- |
| Rule | high_cardinality |
| Severity | info |
| Scope | column |
| Affected column or dataset | material_id |
| Affected records | 3322 |

**Evidence**

- unique count: 3322
- non missing count: 3322
- distinct ratio: 1.0 (100.00%)
- threshold: 0.5 (50.00%)
- median value length: 11.0
- categorical max length: 40
- affected records meaning: distinct non-missing values

**Why this was flagged**

Column 'material_id' is categorical and has 3322 distinct values out of 3322 observed values (distinct-value ratio 1.00), which is at or above the threshold of 0.50. Affected records here means the number of distinct values, not a count of bad rows. This is an observation about cardinality: the column may be an identifier or another near-unique label, and that pattern is often legitimate and useful. It is not evidence that the values are incorrect. Small columns can cross the threshold with only a few distinct labels.

**Suggested action**

Treat this as an observation about distinctness, not as a defect. The column may be an identifier or another near-unique label, which is often legitimate and useful. If it will be used as a category in a grouped analysis, plan for the number of distinct values.

### 10. High cardinality in column 'formula_pretty'

| Field | Value |
| --- | --- |
| Rule | high_cardinality |
| Severity | info |
| Scope | column |
| Affected column or dataset | formula_pretty |
| Affected records | 2817 |

**Evidence**

- unique count: 2817
- non missing count: 3322
- distinct ratio: 0.847983 (84.80%)
- threshold: 0.5 (50.00%)
- median value length: 7.0
- categorical max length: 40
- affected records meaning: distinct non-missing values

**Why this was flagged**

Column 'formula_pretty' is categorical and has 2817 distinct values out of 3322 observed values (distinct-value ratio 0.85), which is at or above the threshold of 0.50. Affected records here means the number of distinct values, not a count of bad rows. This is an observation about cardinality: the column may be an identifier or another near-unique label, and that pattern is often legitimate and useful. It is not evidence that the values are incorrect. Small columns can cross the threshold with only a few distinct labels.

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
