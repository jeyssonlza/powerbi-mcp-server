# Example: Documentation Generation — Technical Docs & Data Dictionary

## Objective
Produce technical documentation and a data dictionary that stay in sync with the model and
can be versioned in Git.

## Example Prompt
```text
Generate the technical documentation (Markdown) and a data dictionary (Markdown + CSV)
for the project currently open, and show me the changelog.
```

## Tools Used
- `generate_documentation` — technical docs in Markdown/HTML
- `generate_data_dictionary` — data dictionary in Markdown, JSON or CSV
- `get_changelog` — per-project change history recorded by the server

## Expected Result
- A technical document describing tables, columns, measures and relationships.
- A data dictionary in the requested format(s).
- The project changelog listing previous tracked changes.

## Professional Use Case
Documentation is usually the first thing to go stale. Generating it from the model itself
keeps it accurate, supports audits and handovers, and gives stakeholders a readable artifact
without opening Power BI. Commit the output to Git for living, versioned documentation.
