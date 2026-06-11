# Example: DAX Measure Workflow — Draft, Validate, Add

## Objective
Create a well-formed DAX measure with a fast validation loop, following best practices
(use `DIVIDE`, `VAR ... RETURN`, explicit format strings).

## Example Prompt
```text
In the Sales table, create a measure "Profit Margin %" =
DIVIDE([Total Profit], [Total Sales]) formatted as "0.0%".
First check the real columns, validate the DAX, then add it.
```

## Tools Used
- `describe_table` — confirm the real columns and types before writing DAX
- `validate_dax` — syntax and reference validation
- `add_measure` — create the measure (with name, format string, description)
- `list_measures` — confirm it was added
- `optimize_dax` — optional suggestions to improve the expression

## Expected Result
- Column/type confirmation so the DAX references real fields.
- A validation report (valid / errors).
- The new `Profit Margin %` measure created with the requested format.

## Professional Use Case
Speeds up measure authoring while enforcing standards (DIVIDE over `/`, variables, consistent
formats, Title Case names) across a team.

> **Orchestration note:** for **complex live models**, the recommended pattern is to validate
> with this server and persist the measure with Microsoft's `powerbi-modeling-mcp` against the
> open model (real Tabular engine), then use this server to document and visualize. See the
> project's orchestration playbook (`AGENTS.md`).
