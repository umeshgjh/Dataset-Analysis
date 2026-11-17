# Final verification

Checked on 17 November 2026 from the project virtual environment (Python 3.12.15, Streamlit 1.67.0, pandas 3.1.1, NumPy 2.5.5, pytest 9.2.0). The project `.venv` did not contain these packages. They were installed from `requirements.txt` with `uv` before the application was started. These checks were run immediately before the submission commit. The project author recorded in the README is umeshgjh.

## Test results

`python -m pytest -q` from the repository root:

```
........................................................................ [ 54%]
...........................................................              [100%]
131 passed in 1.93s
```

The previous baseline was 130. One test was added for the reports-directory confirmation. No existing test was removed or weakened.

`git diff --check` produced no whitespace errors. `smart_inspector/` and `inspector.py` have no diff.

CLI smoke, writing only under `/tmp/sdi-final-2EUm`:

- `examples/research_data.csv`: exit 0, 11 rows, 10 columns, 1 extra duplicate, 8 findings (2 error, 4 warning, 2 info).
- `examples/research_data.json`: exit 0, 4 rows, 5 columns, 1 extra duplicate, 6 findings (0 error, 3 warning, 3 info).
- `examples/lab_observations.json`: exit 0, 8 rows, 6 columns, 0 findings.
- `examples/nested_document.json`: exit 1, unsupported-structure message, no traceback, and no report file.
- `datasets/materials_piezoelectric_properties.csv`: exit 0, 3,322 rows, 15 columns, 0 extra duplicates, 10 info findings.
- `examples/corrupted_observations.csv`: exit 0, 12 rows, 7 columns, 1 extra duplicate, 7 findings (1 error, 4 warning, 2 info).

API smoke: `inspect()` and `DataInspector.inspect()` on the lab file agreed. `to_json()` reported 8 rows and 6 columns, and `to_markdown()` started with the report heading. The research CSV API result had 11 rows, 10 columns, and 8 findings, with no `quality_score`. The nested JSON call raised the unsupported-structure error. Markdown and JSON files for the successful CLI runs were written in the temporary directory above.

Streamlit startup: the application on port 8765 returned HTTP 200. `app.py` parsed, and the installed Streamlit version was 1.67.0.

`reports/`, `datasets/`, and `examples/` have no diff. The sample reports still contain `<redacted local absolute path>` and do not contain `/Users/`. Current documentation has no machine-specific absolute path.

## Browser test results

Streamlit was started with the project virtual environment:

`streamlit run app.py --server.port 8765 --server.headless true`

The page at `http://127.0.0.1:8765/` was opened in the browser tool. This was not limited to Streamlit AppTest.

### Screen widths

- 1440px: empty state, CSV report, nested-JSON error, and the save confirmation.
- 1024px: uploaded-file list, current file, and the session table. Report tables scroll inside their container (client width 564px, content width 768px).
- 640px: with the sidebar collapsed, the heading, uploader, current-file facts, and session table are visible. The expand control is visible. With the sidebar open, it covers the left side of the page; collapsing it reveals the content.

### Upload scenarios

| Scenario | Result |
| --- | --- |
| Initial empty state | "No dataset is loaded." Uploader text is "CSV, JSON". No format selector and no quality score. |
| `examples/research_data.csv` | Detected as csv, 537 bytes. Inspection: 11 rows, 10 columns, 2 error, 4 warning, 2 info. |
| `examples/lab_observations.json` and `examples/research_data.json` together | Both stayed in the session with the CSV. Formats were detected from the names. |
| Switch from the research JSON report to the lab file | Previous downloads disappeared and the status returned to "is ready." |
| Lab inspection | 8 rows, 6 columns, 0 findings. |
| `notes.txt` | The uploader reported "text/plain files are not allowed." The file was not added to the session. |
| `examples/nested_document.json` | Changing to it cleared the previous downloads. Inspection showed the engine message: the root value is an object. No download buttons remained. |
| Empty `empty.csv` | "empty.csv is empty." No downloads. |
| Malformed `bad.csv` (`a,b` then a row of three fields) | "Malformed CSV in bad.csv: row 2 has 3 fields; expected 2 to match the header." No downloads. |
| `examples/corrupted_observations.csv` | 12 rows, 7 columns, 1 error, 4 warning, 2 info. `mm2` and `-42m` were visible. `group_code` was described as categorical. |
| Replace by selecting another session file | The previous report and downloads cleared before the new inspection. |

The page did not ask the user to choose CSV or JSON. The repository copies of the uploaded examples were unchanged. `datasets/materials_piezoelectric_properties.csv` was not uploaded in the browser; its 3,322-row result was checked through the CLI smoke above.

For the successful research CSV report, the page showed file facts and the inspection timestamp, 11 rows and 10 columns, column names and inferred types, missing counts and percentages, unique counts and classification notes, numeric summaries, categorical summaries, duplicate information, all eight findings with severity, rule, column, evidence, explanation, and suggested action, and the configuration used. The corrupted report showed the same sections for its seven findings. No quality score was shown.

### Downloads

Download Markdown and Download JSON for `research_data.csv` requested same-origin files. The response headers named `research_data.csv.inspection.md` and `research_data.csv.inspection.json`. After ignoring the inspection clock, the Markdown matched `InspectionReport.to_markdown()`. After ignoring the clock and the temporary absolute path, the JSON matched `InspectionReport.to_json()`. Both described 11 rows, 10 columns, and 8 findings.

Switching files and failed inspections removed the download buttons. The browser tool does not expose the operating-system download folder, so the check used the files the download buttons requested.

### Save reports and sample protection

The output field defaulted to `/var/folders/.../T/sdi-exports`, outside the repository. Saving the corrupted inspection wrote both report files there and left `reports/` unchanged.

Typing `reports` and choosing Save reports showed: "Saving would replace files in reports/: reports/corrupted_observations.csv.inspection.md, reports/corrupted_observations.csv.inspection.json." The Replace button was not clicked. The sample reports remained unchanged.

### Temporary files

Remove this file deleted `/private/var/folders/.../T/sdi-upload-69al7646` and left the other `sdi-upload-*` directories in place. Downloads for the removed file were cleared.

The two-session lease, the upload older than 24 hours with a current lease, the lock race, unrelated directories, symlinks, and nested directories were executed by pytest, including `test_cleanup_keeps_another_sessions_live_upload_after_24_hours` and `test_cleanup_waits_for_a_lease_refresh_before_deleting`. Those scenarios were not repeated against the live browser session's temporary directory.

### Visual fix

A long list of uploaded files was clipped inside a 106px-high chip area. The uploader chip list now uses its content height, so the chips sit above "Current file" instead of underneath the next section. The rule was checked in the open page, then Streamlit was restarted. The reloaded page's stylesheet includes it.

## Documentation

`README.md`, `docs/demo-script.md`, and `docs/submission-checklist.md` have no `--output-dir reports` command. The demo and checklist write to `$OUT` under the temporary directory. The checklist's last verified count is 131.

## Final recheck

On the same running application, the empty state had no format selector. Uploading `examples/research_data.csv` detected csv and 537 bytes. Inspection reported 11 rows and 10 columns, with file facts, missing values, unique counts, numeric and categorical summaries, duplicates, findings, evidence, suggested actions, and configuration. Download Markdown and Download JSON returned `research_data.csv.inspection.md` (21,488 bytes) and `research_data.csv.inspection.json` (30,407 bytes). The JSON matched `InspectionReport.to_json()` apart from the inspection clock and the temporary upload path. The page did not show a quality score.

The submission commit is authored as `umeshgjh <119152768+umeshgjh@users.noreply.github.com>`, the identity already used on commits `64a9f9e` and `7f1db43` and the GitHub account id 119152768. Stored Git configuration was not changed.

## Remaining limitations

- The command-line default output directory is still `reports/` when `--output-dir` is omitted. The documented commands pass a temporary directory.
- A user can still replace sample reports by choosing "Replace files in reports/". That second click was not executed in the browser.
- At 640px, an open sidebar covers the left side of the page. The collapse control reveals the content.
- File-chip names are shortened by the uploader. A `.txt` file is rejected by Streamlit's type check before the page's own error text.
- A session refreshes its upload lease when the page reruns. After 24 hours without a rerun, that session's uploads can be removed.
- Upload directories created before the ownership marker existed are not removed. The lease lock uses `fcntl` and is for Unix.
- Pointer hover was not screenshotted. Button, table, and severity hover colours are defined in the page CSS.
- The 3,322-row materials file was checked with the CLI, not by uploading it in the browser.
- Commit `7f1db43` still contains the machine path in Git history. The current sample files do not.
