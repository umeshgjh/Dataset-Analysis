# Demonstration script

About two and a half minutes. Run the commands from the repository root with the virtual environment active. Open the Markdown report only when the script says to.

## 0:00 – What the tool does

This is a local inspector for an unfamiliar CSV or JSON table. It reports shape, inferred types, missing values, exact duplicate rows, numeric and categorical summaries, and six quality checks. It does not clean the file, and it does not turn a statistical outlier into a confirmed error.

## 0:25 – Assignment CSV

```bash
python inspector.py inspect datasets/materials_piezoelectric_properties.csv --output-dir reports
```

Say: the file has 3,322 rows and 15 columns, and no extra duplicate row. Open `reports/materials_piezoelectric_properties.csv.inspection.md` at Column Types. `point_group` is categorical. Values such as `1`, `2`, `mm2`, and `-42m` are labels in one code set, so the tool does not report a mean or a mixed-type error. The measurement columns stay numeric. Empty cells are the missing values: six in the band-gap and energy fields, five in the two boolean stability fields. The findings are all informational. The outlier section says these points sit outside the Tukey fences and are not confirmed errors. `material_id` has 3,322 distinct values and `formula_pretty` has 2,817. Those high-cardinality findings describe identifier-like columns. They are useful observations, not defects.

## 1:25 – Nested JSON

```bash
python inspector.py inspect examples/nested_document.json
```

Say: JSON must be a top-level array of flat objects. This file is a root object, so the command exits with status 1 and names the unsupported structure. The original assignment structure file fails the same way. Nested objects and JSON Lines are rejected rather than flattened.

## 1:45 – Flat JSON and the corrupted table

```bash
python inspector.py inspect examples/lab_observations.json --output-dir reports
python inspector.py inspect examples/corrupted_observations.csv --output-dir reports
```

Say: the lab file is a compliant flat array. Eight rows, native numbers and booleans, and no findings. The corrupted file is synthetic and hits every check: missing notes, one duplicate row, mixed batch and score values, one measurement outside the fences, a constant site, and a high-cardinality sample id. `group_code` still shows the code rule, so those symbols are categorical rather than mixed.

## 2:20 – Close

The same engine serves the CLI and `DataInspector`. Markdown and JSON are two views of one result. The checks tell a researcher what to review next. They do not change the dataset.
