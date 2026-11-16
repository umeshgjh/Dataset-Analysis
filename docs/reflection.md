# Reflection

I developed the Smart Data Inspector to help researchers understand unfamiliar datasets without modifying their original contents. The tool supports CSV and JSON inputs, automatically profiles columns, generates statistical summaries, and identifies potential data-quality issues through six explainable checks.

One important implementation decision was to distinguish numerical measurements from categorical codes. For example, values such as `1`, `2`, `mm2`, and `-42m` may represent categories rather than numerical quantities. I refined the type inference logic to recognize such patterns without hardcoding dataset-specific column names. I also ensured that potential outliers are reported as informational findings rather than confirmed errors.

The application uses a modular Python architecture with a reusable API, command-line interface, and Markdown and JSON report generation. It was validated using the assignment's materials dataset, a compliant flat JSON example, and a deliberately corrupted dataset. The implementation passed 93 automated tests, alongside CLI and API verification.

The project took approximately **3 hours** to develop and refine. I used **ChatGPT** for requirements analysis, design decisions, implementation guidance, and code review, and **Cursor with Grok 4.7** for code generation, debugging, refinement, and verification. AI-generated code was checked through source review, automated tests, and execution of the application against demonstration datasets.

A limitation is that nested JSON structures and JSON Lines are not supported. The tool focuses on explainable inspection rather than automatic data cleaning or correction.
