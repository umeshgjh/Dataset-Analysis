# Smart Data Inspector

Smart Data Inspector reads an unfamiliar CSV or JSON table and writes a report of its shape, inferred column types, missing values, duplicate rows, numeric and categorical summaries, and six explainable data-quality checks.

It does not clean the data, assign an overall quality score, or treat a statistical outlier as a confirmed error. The same inspection engine serves the Python API, the command-line interface, and the Streamlit application.

## Authorship

The project author is [umeshgjh](https://github.com/umeshgjh). I conceived, structured, and directed the project. That covered the problem definition and requirements, the system architecture and project structure, the inspection methodology and quality checks, the design and functional decisions, the features to include and the direction of their implementation, and the review, evaluation, and validation of the finished system.

AI coding tools assisted that work under my direction. ChatGPT was used for requirements analysis, implementation guidance, and code review. Cursor, including Grok 4.7, was used for code generation, implementation, debugging, test development, documentation refinement, and code review. I made the architectural and functional decisions and reviewed the resulting implementation.

## Features

- CSV and JSON input, with missing JSON keys treated as missing values.
- Dataset overview: row count, column count, column names, and inferred types.
- Type inference for integer, float, boolean, datetime, categorical, string, mixed, and unknown columns.
- Per-column missing counts and percentages, including which missing token was seen.
- Exact duplicate-row counts.
- Minimum, maximum, and mean for accepted numeric columns.
- Unique count and most frequent value for categorical columns.
- Six quality checks: missingness, duplicate records, mixed types, potential numerical outliers (IQR), constant columns, and high-cardinality categories.
- Each finding has a rule id, title, severity, affected column or dataset, affected-record count when that count means something, evidence, an explanation, and a suggested action.
- Validated configuration, with the settings copied into the report.
- Markdown and JSON reports produced from the same result.
- Deterministic results for the same file and configuration, apart from the inspection timestamp.
- A Streamlit interface for uploading a CSV or JSON file, configuration, inspection, and the same reports.

## Supported formats and limitations

| Format | What is accepted |
| --- | --- |
| `.csv` | UTF-8 text, comma delimiter, one header row, one record per row. A leading byte-order mark is accepted. |
| `.json` | One top-level array of flat objects. Each object is a row. Keys are column names. |

A value may be a string, a finite number, a boolean, or null. A nested object or nested array inside a row is rejected with an error that names the row and field. A top-level object, a non-object row, and JSON Lines are also rejected, and the message says what was found. The format is chosen from the file extension, not by guessing the contents.

Other limits are listed under [Assumptions](#assumptions) and [Known limitations](#known-limitations).

## Requirements

- Python 3.11 or newer
- pandas 2.2 or newer
- NumPy 1.26 or newer
- Streamlit 1.49 or newer, for the browser interface

pytest is included in `requirements.txt` so the test suite can be run after the same install. The tool was developed and checked with Python 3.12, pandas 3.1, and NumPy 2.5.

## Installation

From the repository root:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If `python3` on your machine is older than 3.11, create the environment with a 3.11+ interpreter. With [uv](https://docs.astral.sh/uv/), install into the environment with `uv pip` (a uv-created environment does not include `pip` unless you seed it):

```bash
uv python install 3.12
uv venv --python 3.12 .venv
uv pip install -r requirements.txt --python .venv/bin/python
source .venv/bin/activate
```

`inspector.py` and `python -m smart_inspector` both work when the repository root is the working directory. The package does not need a separate editable install. The same inspection is available in the browser with `streamlit run app.py`; see [Frontend](#frontend).

On Python 3.9 the command exits with a short version error and no traceback.

## Command-line usage

```bash
OUT="${TMPDIR:-/tmp}/sdi-reports"
mkdir -p "$OUT"
python inspector.py inspect examples/research_data.csv --output-dir "$OUT"
python inspector.py inspect examples/research_data.json --config examples/config.json --output-dir "$OUT"
python inspector.py inspect data.csv --output-dir "$OUT" --format both
python inspector.py inspect data.csv --output-dir "$OUT" --format markdown
python inspector.py inspect data.csv --output-dir "$OUT" --missingness-threshold 0.1 --outlier-multiplier 3
python inspector.py inspect data.csv --output-dir "$OUT" --disable-check outliers --disable-check high_cardinality
python inspector.py --help
python -m smart_inspector inspect examples/research_data.csv --format json --output-dir "$OUT"
```

`--format` is `markdown`, `json`, or `both` (the default). Reports are written to `--output-dir`, which defaults to `reports` and is created if needed. File names keep the source extension so `data.csv` and `data.json` do not overwrite each other. The commands above pass a temporary directory so a fresh run does not replace the committed samples. A newly generated report records the absolute path of the file on the machine that ran the inspection. The sample reports already in `reports/` keep the relative path and omit that machine-specific absolute path:

- `reports/research_data.csv.inspection.md`
- `reports/research_data.csv.inspection.json`

Exit codes:

| Code | Meaning |
| --- | --- |
| 0 | Inspection finished and the requested reports were written. |
| 1 | The file could not be inspected (missing path, unsupported type, malformed contents, empty table). |
| 2 | The command or the configuration is invalid. |

Ordinary failures print `Error: ...` on stderr. Add `--debug` to include a traceback.

`examples/research_data.csv` is a small synthetic table, not a real study. Inspecting it reports 11 rows, 10 columns, 1 extra duplicate row, and 8 findings:

| Severity | Rule | Where | What it shows |
| --- | --- | --- | --- |
| error | missingness | `unused` | Every value is empty or `n/a`. |
| warning | duplicates | dataset | Row 11 repeats row 1. |
| warning | mixed_types | `observed_on` | `not-a-date` is not a year-first date. |
| warning | mixed_types | `amount` | `bad` is left out of the numeric summary. |
| error | mixed_types | `code` | Digits and labels are mixed, so no numeric mean is reported. |
| info | outliers | `measurement` | `100` sits outside the IQR fences. It is not called an error. |
| warning | constant_columns | `source` | Every observed value is `lab`. |
| info | high_cardinality | `record_id` | 10 distinct ids out of 11 rows. |

`examples/research_data.json` is the JSON counterpart: native numbers and booleans, a JSON null, a key omitted on one row, a real zero, and one duplicated object.

## Quality checks

Each finding has a rule id, title, severity, column or dataset scope, an affected-record count when that count has a clear meaning, evidence, an explanation, and a suggested action. Severities separate definite structural problems from things that only need review.

| Rule | Severity | What is flagged |
| --- | --- | --- |
| `missingness` | warning, or error at 90% or more | Missing fraction strictly greater than `missingness_threshold`. |
| `duplicates` | warning | One or more extra exact copies. This does not prove the rows are wrong. |
| `mixed_types` | error when the column is `mixed`; warning when a type was accepted but some values do not fit | Values that disagree with the dominant kind. They are not coerced. |
| `outliers` | info | Numeric values strictly outside the Tukey fences. The finding calls them potential outliers, not confirmed errors. |
| `constant_columns` | warning | Exactly one distinct non-missing value. An all-missing column is not constant. |
| `high_cardinality` | info | A categorical column whose distinct-value ratio is at least `high_cardinality_threshold`, with at least two distinct values. The affected-record count is the number of distinct values. This is an observation about an identifier or another near-unique label, not a claim that the values are wrong. |

## Demonstration data

| File | Role |
| --- | --- |
| `datasets/materials_piezoelectric_properties.csv` | Unchanged copy of the assignment CSV (3,322 rows, 15 columns). |
| `examples/lab_observations.json` | Compliant flat JSON: eight generic lab rows and no quality findings. |
| `examples/corrupted_observations.csv` | Synthetic table that triggers all six checks. `group_code` uses values such as `1`, `2`, `mm2`, and `-42m` and is classified as categorical. |
| `examples/nested_document.json` | Tiny synthetic root object. It is not the assignment file. It produces the same class of rejection. |
| `examples/research_data.csv` | Smaller synthetic table used by the first examples above. |

The assignment structure file, `materials_piezoelectric_structures.json`, is a 22 MB top-level object and is not stored in this repository. Inspecting it exits with status 1 and prints:

```text
Error: Unsupported JSON structure: the root value is an object. Provide a top-level array of flat objects. Nested documents and JSON Lines are not supported.
```

```bash
OUT="${TMPDIR:-/tmp}/sdi-reports"
mkdir -p "$OUT"
python inspector.py inspect datasets/materials_piezoelectric_properties.csv --output-dir "$OUT"
python inspector.py inspect examples/lab_observations.json --output-dir "$OUT"
python inspector.py inspect examples/corrupted_observations.csv --output-dir "$OUT"
python inspector.py inspect examples/nested_document.json --output-dir "$OUT"
```

Those commands write new reports under `$OUT`. The repository already contains these committed samples, with the local absolute path removed:

- `reports/materials_piezoelectric_properties.csv.inspection.md`
- `reports/materials_piezoelectric_properties.csv.inspection.json`
- `reports/lab_observations.json.inspection.md`
- `reports/lab_observations.json.inspection.json`
- `reports/corrupted_observations.csv.inspection.md`
- `reports/corrupted_observations.csv.inspection.json`

On the assignment CSV the tool reports 3,322 rows, 15 columns, and 0 extra duplicate rows. `point_group` is categorical (21 labels, mode `mm2`). Empty cells are the only missing values: 6 in `band_gap`, `is_metal`, `formation_energy_per_atom`, and `energy_above_hull`, and 5 in `is_stable` and `theoretical`. The 10 findings are all `info`: IQR outliers on the numeric columns, plus high cardinality for `material_id` and `formula_pretty`.

`examples/corrupted_observations.csv` reports 12 rows, 1 extra duplicate row, and 7 findings covering all six rules: missing `notes` (6 of 12 values, warning), duplicate rows (warning), mixed `batch` (error) and `score` (warning), an info outlier on `measurement`, constant `site`, and high-cardinality `sample_id`. `group_code` is categorical and is not flagged as mixed.

The nested-document command exits with status 1 and does not write a report.

## Python API

```python
import tempfile
from pathlib import Path

from smart_inspector import DataInspector

inspector = DataInspector("examples/research_data.csv")
report = inspector.inspect()
output = Path(tempfile.mkdtemp(prefix="sdi-reports-"))
report.to_markdown(output / "research_data.csv.inspection.md")
report.to_json(output / "research_data.csv.inspection.json")

custom = DataInspector(
    "examples/research_data.csv",
    config={
        "missingness_threshold": 0.1,
        "outlier_multiplier": 3,
        "enabled_checks": ["missingness", "duplicates", "outliers"],
    },
)
custom_report = custom.inspect()
```

`inspect()` reads the file and returns an `InspectionReport`. It does not write a file and it does not modify the source. Call `inspect()` again to re-read the file. `to_markdown` and `to_json` return the text and, when given a path, write it. Parent directories are created.

`DataInspector` accepts an `InspectionConfig` or a mapping. A bad configuration raises `ConfigError` before the file is read. File and parse problems raise `InspectionError` (or a subclass such as `FileInputError`, `ParseError`, or `EmptyDataError`) from `inspect()`.

```python
from smart_inspector import InspectionConfig, inspect

report = inspect(
    "examples/research_data.json",
    config=InspectionConfig(outlier_multiplier=3),
)
```

The CLI calls this same engine.

## Configuration

Defaults are suitable for a first look at an unfamiliar table. Pass a mapping, an `InspectionConfig`, or a JSON object via `--config`. Command-line flags override the file. Unknown option names are rejected.

```json
{
  "missingness_threshold": 0.2,
  "outlier_method": "iqr",
  "outlier_multiplier": 1.5,
  "outlier_min_samples": 4,
  "high_cardinality_threshold": 0.5,
  "categorical_max_length": 40,
  "dominance_threshold": 0.8,
  "enabled_checks": [
    "missingness",
    "duplicates",
    "mixed_types",
    "outliers",
    "constant_columns",
    "high_cardinality"
  ],
  "missing_tokens": ["#n/a", "#na", "<na>", "n/a", "nan", "nat", "none", "null"]
}
```

`examples/config.json` contains these defaults.

| Option | Default | Rule |
| --- | --- | --- |
| `missingness_threshold` | `0.2` | Flag a column when its missing fraction is **strictly greater** than this value. `0` and `1` are allowed. |
| `outlier_method` | `"iqr"` | Only `iqr` is implemented. `IQR` is accepted and stored as `iqr`. |
| `outlier_multiplier` | `1.5` | Tukey fence multiplier. Must be finite and greater than 0. |
| `outlier_min_samples` | `4` | Skip the outlier check when fewer numeric values are available. |
| `high_cardinality_threshold` | `0.5` | Flag a categorical column when its distinct-value ratio is **greater than or equal** to this value. |
| `categorical_max_length` | `40` | Median label length at or below this, and no newlines, classifies text as categorical. |
| `dominance_threshold` | `0.8` | A type is accepted only when it covers at least this share. Must be greater than `0.5` and at most `1`. |
| `enabled_checks` | all six | Replaces the full set. An empty list turns the findings off and still computes the descriptive profile. |
| `missing_tokens` | the list above | Replaces the defaults. Matching ignores case and surrounding space. |

Turning a check off does not remove the corresponding descriptive section. Duplicate counts, missing percentages, and numeric summaries are still reported.

A custom missing-token list does not extend the defaults. To add a token, pass the defaults plus the new token:

```python
from smart_inspector import DEFAULT_MISSING_TOKENS, InspectionConfig

config = InspectionConfig(missing_tokens=[*DEFAULT_MISSING_TOKENS, "missing", "na"])
```

`ALL_CHECKS` is exported for the same reason.

## Reports

Markdown and JSON are two views of one payload. Markdown rounds displayed numbers (6 decimal places, percentages to 2 decimal places). JSON keeps full precision and is strict JSON: `NaN` and infinity are not emitted.

Both reports include:

1. Dataset overview.
2. Input file path, format, size, encoding, and the Python, pandas, and NumPy versions used.
3. Column names, inferred type, dominant type, and a classification note.
4. Missing-value counts, percentages, and token breakdowns.
5. Duplicate-row count, with the definition of an exact duplicate.
6. Numeric summaries, or an explicit statement that no numeric column was accepted.
7. Categorical summaries, or an explicit statement that no categorical column was accepted.
8. Data-quality findings with explanations and suggested actions.
9. The configuration that produced the report.
10. Inspection timestamp in UTC (`YYYY-MM-DDTHH:MM:SSZ`) and tool version `1.0.0`.

Severities:

- `error`: the column has no stable type, or at least 90% of its values are missing.
- `warning`: a likely quality issue that can still be legitimate, such as duplicates, a constant field, moderate missingness, or a minority of mismatched values.
- `info`: something to review that is not a confirmed error. Outliers are potential anomalies. High cardinality means the column has many distinct values, often because it is an identifier or another useful near-unique label.

There is no overall quality score.

## Architecture

```text
smart_inspector/
├── __init__.py          public API
├── __main__.py          python -m smart_inspector
├── version.py           tool name and version
├── exceptions.py        errors safe to show on the CLI
├── definitions.py       wording shared by both report formats
├── config.py            validated settings
├── values.py            cell rules: missing, type, identity, display
├── loader.py            CSV and JSON readers, object-dtype table
├── inference.py         column type decisions
├── profiler.py          shape, duplicates, numeric and categorical summaries
├── quality.py           the six checks
├── inspector.py         DataInspector and report assembly
├── cli.py               argparse command line
└── reporters/
    ├── markdown.py
    └── json_report.py
inspector.py             CLI entry point
app.py                   Streamlit interface over inspect() and write_reports
tests/                   pytest fixtures, including the example and assignment files
examples/                small demo files
datasets/                unchanged assignment CSV
reports/                 inspection reports
docs/                    reflection, demo script, and submission checklist
```

`values.py`, `exceptions.py`, `cli.py`, `definitions.py`, and `version.py` are extra modules so that one rule is not copied into the loader, the profiler, and the checks. Pandas holds the aligned table as object columns and supplies its shape. It is not used to decide types or duplicates: pandas would treat `True` as equal to `1`, and its dtypes would hide the text that failed to parse. NumPy computes means and linear percentiles. After the table is built, a check refuses to continue if any cell's Python type changed.

## Assumptions

- The file fits in memory. The whole table is loaded before profiling.
- CSV uses commas and a header. Completely blank lines are ignored. A quoted field may contain commas and newlines. Every column name must be non-blank, and names are case-sensitive. Duplicate names are an error.
- JSON objects may omit keys. An omitted key and a JSON null are both missing, and the report counts them separately as `<absent>` and `<null>`. Non-standard JSON `NaN` is missing. `Infinity` is rejected.
- Duplicate JSON keys are an error. Standard JSON parsers would otherwise keep one of them silently.
- Missing tokens, compared after trimming and lower-casing, are `#n/a`, `#na`, `<na>`, `n/a`, `nan`, `nat`, `none`, and `null`, plus empty or whitespace-only text. `0`, `false`, `"0"`, `"false"`, and bare `NA` are real values unless you add those tokens yourself.
- Boolean words are `true`, `false`, `yes`, and `no`, in any letter case. `y`, `n`, `1`, and `0` are not booleans.
- Integers do not have leading zeros, so `007` stays text. Floats use a decimal point or an exponent, such as `1.5` or `1.5e1`.
- Dates must be year-first: `YYYY-MM-DD` or `YYYY/MM/DD`, with an optional time and timezone. Month and day must be two digits. `01/02/2024` is text, because the tool does not choose a locale. A column of only years, such as `2024`, is an integer.
- The dominant type is the compatible kind that covers the most non-missing values. Integers are compatible with float. Ties prefer boolean, then datetime, then integer, then float, then string, which keeps an all-integer column from being called float.
- If that coverage is at least the dominance threshold, the type is accepted and the other values are listed as unexpected. Otherwise the column is `mixed`, apart from the short-code exception below. An all-missing column is `unknown`.
- Text is categorical when the median stripped length is at most `categorical_max_length` and no value contains a newline. Longer text is `string`.
- A short-token column is also categorical when it mixes integer-like tokens with letter-and-digit codes that use at least two alphabetic patterns. The pattern is the letters left after digits and signs are removed, so `mm2` and `-42m` are different patterns, while `bad0` and `bad1` are the same pattern and stay on the mixed or numeric path. Integer-like tokens in an accepted code column are labels: they are not unexpected values and they do not get a mean. The exception does not run when integer or float coverage already meets the dominance threshold, or when any value is a float, boolean, date, has whitespace, or is longer than the label limit.
- Unique counts and duplicate comparisons use the stored value. `"1"` and `" 1"` are different text, while both still parse as the integer 1 in a numeric summary. Categories are not case-folded.
- An exact duplicate matches on every column. All missing representations match each other. `true` is not a duplicate of `1`, and the string `"1"` is not a duplicate of the number `1`. The reported duplicate count is the number of extra copies after the first occurrence.
- Numeric min, max, and mean, and the IQR check, run only after a column is accepted as integer or float. Unexpected non-numeric cells are excluded and counted. Mixed columns do not get a mean.
- Outliers use Tukey fences. Q1 and Q3 are linear percentiles at position `(n - 1) * p`. The lower fence is `Q1 - k * IQR` and the upper fence is `Q3 + k * IQR`. A value is listed only when it is strictly below the lower fence or strictly above the upper fence. Values on a fence are not outliers. The check needs at least `outlier_min_samples` finite numbers.
- The most frequent categorical value is the earliest value that reaches the highest count.
- Results do not depend on column names from any particular dataset. Row numbers in findings are 1-based data rows and do not count the CSV header.

## Known limitations

- Only comma-separated CSV and a single JSON array are supported. Semicolon CSV, Excel, Parquet, and JSON Lines are out of scope.
- Datetimes are limited to the unambiguous year-first forms above. A single datetime column may still mix `2024-01-01` and `2024-01-01T00:00:00`; that is reported in the classification note, not as a seventh quality rule.
- High cardinality applies to categorical text, not to numeric identifiers. Unique counts for numeric columns are still in the column profile.
- A short unique column can be classified as categorical and then flagged as high cardinality. That is intentional for ids such as `record_id` and `material_id`. Free text whose median length is above 40 characters is `string` and is not flagged by that rule.
- Code columns are recognized only in the situation described above. A numeric column that still meets the dominance threshold keeps its numeric type, even if a few cells look like codes. Letter-and-digit tokens that all share one alphabetic pattern are not rewritten into a category. A code column that also contains a decimal, a date, or a boolean stays on the ordinary mixed or numeric path.
- Constant columns are not also flagged as high cardinality.
- Integers that do not fit in a finite float still report an exact minimum and maximum. The mean and the outlier check are skipped, and the report says why.
- Samples of unexpected values and outliers are capped at 10, and embedded text is capped at 200 characters. Counts in the evidence are complete.
- The tool loads the full file into memory and is aimed at inspection, not at a streaming warehouse job.
- There is no imputation, no row deletion, and no overall score.

## Frontend

The Streamlit page calls `inspect()` and renders `InspectionReport.to_dict()`. Configuration is an `InspectionConfig`. Saved reports go through `write_reports`, the same writer as the command line. The page inspects files you upload and can write report files. It does not load a dataset on startup, and it does not modify the uploaded file. The files in `datasets/` and `examples/` remain available to the command line, the API, and the tests.

From the repository root, with the virtual environment activated:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

**Dataset.** The page opens with an upload area and no dataset selected. Choose a `.csv` or `.json` file, or drop it on the page. The uploader accepts only those two extensions. The format is taken from the file name; the page does not ask you to pick CSV or JSON. Another extension is refused before inspection, and the inspection engine still checks the contents of an accepted file. After the upload it shows the file name, detected format, size, and modification time. The bytes are copied to a temporary directory outside the repository. Each session keeps a lease on its directories and refreshes that lease while the page is in use. A directory is removed only after its lease has been idle for 24 hours. A lease that is still current keeps the directory, even when the upload itself is older than 24 hours. Upload another file to inspect that file instead. **Remove this file** deletes only the temporary copy. Several uploads can stay in the session, and the sidebar chooses which one is current. Changing the current file clears the previous report, so a download cannot belong to a file you are no longer viewing.

**Configuration.** The form exposes every inspection option: missingness, the IQR multiplier, the outlier sample minimum, high cardinality, categorical label length, the dominance threshold, the six checks, and the missing-token list. Outlier method stays `iqr`, which is the only implemented method. **Apply configuration file** uses the command-line config reader on a JSON file you supply. **Reset to defaults** restores `InspectionConfig`. **Download configuration** writes a JSON object that can be loaded again. Invalid configuration shows the validator's message.

**Inspection and reports.** **Inspect dataset** runs the engine. The page then shows the file and runtime facts, the dimensions and column names, column types and classification notes, missing values, duplicate rows and their definition, numeric summaries, categorical summaries, every finding, the configuration copied into the report, and the definitions. **Download Markdown** and **Download JSON** are `to_markdown()` and `to_json()` for that inspection. **Save reports** writes `{filename}.inspection.md` and `{filename}.inspection.json` into the chosen directory. The default is a temporary `sdi-exports` directory outside the repository, so a normal save does not replace the committed samples. Type another path to choose a different location. If that path is `reports/` and a report file already exists there, the page asks for confirmation before replacing it. Saving into `datasets/` or `examples/` is refused. A file the engine cannot inspect shows that error and clears the previous result, including its downloads. **Include error details** adds the traceback, which is the `--debug` choice.

**Developer.** **Run tests** executes `python -m pytest -q` in the repository. The command cannot be edited on the page.

These stay in the terminal:

- Creating the virtual environment and installing dependencies.
- `python inspector.py` and `python -m smart_inspector` when a script needs the process exit code (`0` success, `1` file or parse error, `2` configuration error).
- Git, and edits to the inspection package.

## Verification

With the virtual environment activated, from the repository root:

```bash
pytest
OUT="${TMPDIR:-/tmp}/sdi-reports"
mkdir -p "$OUT"
python inspector.py inspect examples/research_data.csv --output-dir "$OUT"
python inspector.py inspect examples/research_data.json --config examples/config.json --output-dir "$OUT"
python inspector.py inspect datasets/materials_piezoelectric_properties.csv --output-dir "$OUT"
python inspector.py inspect examples/lab_observations.json --output-dir "$OUT"
python inspector.py inspect examples/corrupted_observations.csv --output-dir "$OUT"
python - << 'PY'
import tempfile
from pathlib import Path
from smart_inspector import DataInspector
report = DataInspector("examples/research_data.csv").inspect()
print(report)
assert report.to_dict()["overview"]["row_count"] == 11
output = Path(tempfile.mkdtemp(prefix="sdi-reports-"))
report.to_markdown(output / "research_data.csv.inspection.md")
report.to_json(output / "research_data.csv.inspection.json")
print(output)
PY
```

These commands write new reports to a temporary directory. They do not modify the committed files in `reports/`.

`pytest` does not download data. It covers CSV and JSON parsing, missing values, type inference, numeric and categorical summaries, duplicate detection, all six quality checks, Markdown and JSON output, invalid paths, empty inputs, nested JSON, configuration validation, the demonstration files, and the assignment CSV. The reflection, demonstration script, and submission checklist are in `docs/reflection.md`, `docs/demo-script.md`, and `docs/submission-checklist.md`.

A successful CSV inspection prints a short summary and writes both report files. The process exit code is 0.
