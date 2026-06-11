# Example: Power BI Project Analysis — Quality & Governance Audit

## Objective
Audit a semantic model before a release: data quality, relationship health, schema shape and
best-practice compliance.

## Example Prompt
```text
Open the PBIP at C:\PowerBI\Finance and run a full review:
data quality, relationship diagnostics, schema classification and best practices.
Summarize the issues by severity.
```

## Tools Used
- `open_project` — load the project
- `analyze_data_quality` — nulls, duplicates, type issues, outliers
- `profile_data` — per-column profiling and distributions
- `diagnose_relationships` — broken, ambiguous, bidirectional or isolated relationships
- `classify_schema` — star / snowflake / undetermined
- `run_best_practices` — model best-practice checks

## Expected Result
- A consolidated report of data-quality findings per table/column.
- A list of relationship problems with the affected tables.
- The detected schema type and any modeling smells.
- Prioritized best-practice recommendations.

## Professional Use Case
A repeatable "model health check" for BI teams: run it before promoting a report to
production, during audits, or when taking over a model from another developer. The output
doubles as documentation for a governance review.
