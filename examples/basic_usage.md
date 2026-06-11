# Example: Basic Usage — Open and Explore a Project

## Objective
Open a Power BI PBIP project and understand its structure (tables, measures, relationships)
before doing any work.

## Example Prompt
```text
Open the PBIP project at C:\PowerBI\Sales, then give me an overview:
list the tables and describe the Sales table.
```

## Tools Used
- `open_project` — load the PBIP project from disk
- `project_info` — high-level project metadata
- `project_structure` — file/folder tree of the project
- `list_tables` — all tables in the semantic model
- `describe_table` — columns, data types and measures of a table

## Expected Result
- The project is loaded into the active session.
- A list of tables with row/column counts where available.
- For `Sales`: its columns (name, data type), measures and partition info.

## Professional Use Case
The first step in any BI engagement: quickly map an unfamiliar model before changing
anything. Useful for code review, onboarding onto an existing report, or assessing a model
you inherited — without opening Power BI Desktop.
