# Submission checklist

The items below match the Smart Data Inspector assignment: a local CSV and JSON inspector, both report formats, explainable checks, a README, tests, and a short demonstration. Do not send the assignment email from this repository.

## Application

- [ ] `smart_inspector` package, `inspector.py`, and `python -m smart_inspector` are present and use the same engine.
- [ ] CSV input is UTF-8, comma-separated, and has a header.
- [ ] JSON input is a top-level array of flat objects. Missing keys are missing values.
- [ ] Nested JSON is rejected. `python inspector.py inspect examples/nested_document.json` exits 1 with an unsupported-structure message and no traceback.
- [ ] The six checks are present: missingness, duplicates, mixed types, outliers, constant columns, and high cardinality.
- [ ] Outlier findings stay `info` and say they are not confirmed errors.
- [ ] High-cardinality findings stay `info` and describe identifier-like columns. They do not call `material_id` or `formula_pretty` defective.
- [ ] Configuration is validated. `examples/config.json` matches the documented defaults.
- [ ] The tool does not clean the source file and does not emit an overall quality score.

## Assignment data and demonstrations

- [ ] `datasets/materials_piezoelectric_properties.csv` is the unchanged assignment CSV.
- [ ] `python inspector.py inspect datasets/materials_piezoelectric_properties.csv --output-dir reports` exits 0: 3,322 rows, 15 columns, 0 extra duplicates.
- [ ] `point_group` is categorical, with 21 labels and mode `mm2`. It has no numeric mean.
- [ ] Empty cells are the only missing values: 6, 6, 6, 6, 5, and 5 on the six columns named in the README.
- [ ] That CSV has 10 findings, all `info`: outliers on the numeric columns, plus high cardinality for `material_id` (3,322) and `formula_pretty` (2,817).
- [ ] `examples/lab_observations.json` inspects as 8 rows and 0 findings.
- [ ] `examples/corrupted_observations.csv` inspects with all six rule ids.
- [ ] Markdown and JSON reports exist for the assignment CSV, the flat JSON example, and the corrupted CSV, and they describe the same results.

## Documentation and verification

- [ ] README install, CLI, API, configuration, limitations, and report paths match the commands that were run.
- [ ] `pytest` passes. The expected result is 93 passed.
- [ ] `docs/demo-script.md` can be spoken in about 2–3 minutes against the commands above.
- [ ] `docs/reflection.md` is under 300 words and records about 3 hours, ChatGPT, Cursor with Grok 4.7, and the checks used on generated code.
- [ ] No virtual environment, cache, secret, or unrelated personal file is staged. Generated reports, demonstration data, and documentation are included.

## Git

- [ ] The initial commit `64a9f9e` is unchanged.
- [ ] Commit and push only after this review is accepted.
