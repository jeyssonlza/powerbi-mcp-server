# Power BI MCP Server

**A professional Model Context Protocol (MCP) server that lets AI assistants analyze, document, secure and apply AI/ML to Power BI projects (PBIP/PBIX) through natural language — pairing with Microsoft's official MCP for model authoring.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-compatible-7e56c2.svg)](https://modelcontextprotocol.io/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Commercial License](https://img.shields.io/badge/Commercial_License-Available-orange.svg)](COMMERCIAL_LICENSE.md)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![CI](https://github.com/jeyssonlza/powerbi-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/jeyssonlza/powerbi-mcp-server/actions/workflows/ci.yml)

---

## Executive Summary

**Power BI MCP Server** turns any MCP-compatible AI assistant (Claude, etc.) into a hands-on
Power BI engineering co-pilot. Instead of manually editing dozens of JSON/TMDL/PBIR files,
a BI developer describes the goal in plain language and the server executes it through **66
controlled tools** spanning project management, semantic modeling, AI/ML analytics,
visualization, documentation, security and Power BI Service integration.

It is built for **PBIP** projects — the text-based, version-control-friendly format — so that
modeling, auditing and automation become reproducible engineering workflows rather than
manual clicking. The codebase follows a modular `src` layout with Pydantic models, full type
hints, domain exceptions, automated backups and an audited write path.

> **What it is:** a complete automation layer for Power BI PBIP projects — create **native
> Power BI visuals**, run AI/ML analytics, generate documentation, enforce security and validate
> DAX, all from natural language without opening Power BI Desktop.
>
> **What it is NOT:** a replacement for *building* the semantic model. For authoring tables,
> measures and relationships against a live model, pair it with Microsoft's official
> `powerbi-modeling-mcp` (see [Difference from Microsoft](#difference-from-microsoft-power-bi-mcp)).
> The two work as a team: Microsoft's MCP builds the model, this server does everything else.

## What Problem It Solves

BI teams lose hours on repetitive, error-prone manual work:

- Understanding and reviewing semantic models scattered across many TMDL/PBIR files.
- Validating DAX without a fast feedback loop.
- Producing and maintaining technical documentation and data dictionaries.
- Running ad-hoc analytics (anomalies, forecasting, segmentation) outside the model.
- Keeping backups, audit trails and PII controls consistent.

This project collapses those tasks into natural-language requests backed by deterministic,
tested tools — with automatic backups and an audit log so changes stay safe and traceable.

## Why MCP Matters for Power BI Automation

The **Model Context Protocol** is an open standard that lets AI assistants call external
tools through a well-defined contract. For Power BI, that means:

- **Natural language → real actions**: "validate this measure", "document the model",
  "forecast sales" become concrete tool calls, not just chat.
- **Reproducible & auditable**: every tool has typed inputs/outputs, backups and logging.
- **Composable**: the same tools work from any MCP client (Claude Code, VS Code, OpenCode,
  Codex, etc.), and can be orchestrated alongside other MCP servers.

## Key Features

- **Project lifecycle (10 tools)** — open/inspect PBIP projects, structure exploration,
  automatic backups, restore, and PBIP→PBIX conversion (via `pbi-tools` when available).
- **Semantic model (22 tools)** — inspect tables/columns/measures/relationships, **validate
  DAX**, diagnose relationships (broken/ambiguous/bidirectional/isolated) and classify schema
  (star/snowflake). Reads PBIP projects built by Microsoft's MCP and analyzes the full result.
- **AI/ML analytics (8 tools)** — anomaly detection, clustering, time-series forecasting,
  RFM segmentation, correlation matrices, explainable decision trees, regression and
  classification — with optional integration of results back into the model.
- **Visuals & reports (7 tools)** — **native Power BI visuals and pages (PBIR)**, KPI cards,
  auto-layout dashboards, Power BI themes, and optional Plotly HTML exports for external use.
- **Analysis & docs (8 tools)** — data quality, profiling, static performance review, best
  practices, technical documentation (Markdown/HTML), data dictionary and per-project
  changelog.
- **Security (6 tools)** — PII masking, deterministic HMAC surrogate keys, value
  encryption/decryption and audit-log access.
- **Power BI Service (5 tools)** — list workspaces/datasets/reports, execute DAX and trigger
  dataset refreshes via the REST API.

## Difference from Microsoft Power BI MCP

This project is **complementary** to Microsoft's official `powerbi-modeling-mcp`, not a
replacement. The two operate on different surfaces and are best used together:

| Aspect | Microsoft `powerbi-modeling-mcp` | **This project (`powerbi`)** |
|--------|----------------------------------|------------------------------|
| Target | **Live model** in Power BI Desktop (TOM/AMO) | **PBIP/PBIX files on disk** |
| Power BI state | Requires Desktop **open** | Works with Desktop **closed** |
| Core strength | Writing the model, executing real DAX, calculation groups, performance trace | Native Power BI visuals (PBIR), AI/ML analytics, data quality, documentation, security/PII |
| Best for | Authoring and validating the semantic model against the live engine | Local/professional automation, analysis, governance and reporting |

A practical, respectful division of labor: **let Microsoft's engine write and validate the
model in a live session, and use this server to analyze, document, secure and visualize the
result.** This project focuses on local/professional automation of PBIP/PBIX projects,
semantic-model analysis, technical documentation, DAX validation, visual generation, applied
AI/ML, and auditing/governance for BI development workflows.

## Architecture Overview

```text
src/powerbi_mcp/
├── server.py          # MCP server (stdio) + tool registration
├── session.py         # active project session
├── config.py          # settings (env / .env, PBIMCP_ prefix)
│
├── core/              # archive, backup, exceptions, logger, validators
├── pbip/              # models, reader, writer, parser, pbix
├── model/             # tables, columns, relationships, measures, dax_validator
├── ai/                # anomaly, clustering, forecasting, rfm, correlation,
│                      #   decision_tree, regression, classification, integration
├── visuals/           # builder, pbip_visuals, html_visuals, themes, pages
├── analysis/          # data_quality, profiling, performance, best_practices
├── docs/              # generator, data_dictionary, changelog
├── security/          # encryption, surrogate_keys, masking, audit
├── powerbi_api/       # auth, client (Power BI REST API)
└── tools/             # 8 MCP tool domains (project, model, ai, visuals,
                       #   analysis, docs, security, pbi_api)
```

Design: `src` layout, `pyproject.toml`, Pydantic models, `py.typed` typing, domain-specific
exceptions, and functional package separation. Tool count is verifiable with
[`scripts/count_tools.py`](scripts/count_tools.py).

## MCP Tools (66)

| Domain | Tools |
|---|---|
| **Project** (10) | `open_project`, `project_info`, `project_structure`, `reload_project`, `close_project`, `create_backup`, `list_backups`, `restore_backup`, `convert_to_pbix`, `read_pbix_info` |
| **Model** (22) | `list_tables`, `describe_table`, `list_measures`, `list_relationships`, `search_objects`, `add_table`, `add_calculated_table`, `rename_table`, `delete_table`, `add_data_column`, `add_calculated_column`, `update_column`, `delete_column`, `add_measure`, `update_measure`, `delete_measure`, `validate_dax`, `add_relationship`, `update_relationship`, `delete_relationship`, `diagnose_relationships`, `classify_schema` |
| **AI** (8) | `detect_anomalies`, `run_clustering`, `forecast_series`, `rfm_segmentation`, `correlation_analysis`, `decision_tree_explain`, `train_regression`, `train_classification` |
| **Visuals** (7) | `list_pages`, `create_page`, `create_visual`, `create_dashboard`, `export_html_visual`, `list_color_palettes`, `create_theme` |
| **Analysis** (5) | `analyze_data_quality`, `profile_data`, `analyze_performance`, `run_best_practices`, `optimize_dax` |
| **Docs** (3) | `generate_documentation`, `generate_data_dictionary`, `get_changelog` |
| **Security** (6) | `mask_data`, `generate_surrogate_keys`, `encrypt_value`, `decrypt_value`, `generate_encryption_key`, `get_audit_log` |
| **Power BI Service** (5) | `pbi_list_workspaces`, `pbi_list_datasets`, `pbi_list_reports`, `pbi_execute_dax`, `pbi_refresh_dataset` |

> See [`examples/`](examples/) for end-to-end professional workflows.

## Use Cases for BI Teams

- **Model review & governance** — open a PBIP, diagnose relationships, classify the schema
  and run best-practice checks before a release.
- **DAX productivity** — draft, validate and document measures with immediate feedback.
- **Living documentation** — auto-generate technical docs and a data dictionary that stay in
  sync with the model, versioned in Git.
- **Embedded analytics** — run forecasting/anomaly detection on project data and surface the
  results as DAX calculated tables or Power Query.
- **Data protection** — mask PII and generate deterministic surrogate keys for shareable
  samples.
- **Audit & safety** — every write is backed up and logged, supporting compliance reviews.

## Example Prompts

```text
Open the PBIP project at C:\PowerBI\Sales and list its tables.
```
```text
Validate this DAX measure and check best practices:
CALCULATE([Total Sales], SAMEPERIODLASTYEAR(Date[Date]))
```
```text
Create a page called "Executive Summary" with a column chart of
Product[Name] by SUM(Sales[Amount]).
```
```text
Detect anomalies in sales.csv on the Amount column and integrate the result
as a DAX calculated table named SalesAnomalies.
```
```text
Generate the technical documentation and data dictionary for this project.
```

## Demo Workflow

End-to-end validated workflow — from raw data to a fully functional PBIX with model, visuals
and documentation, **without a single manual click on the report canvas**:

**Phase 1 — Model (Power BI Desktop open + Microsoft MCP)**

1. Load source tables in Power BI Desktop (Power Query).
2. Microsoft MCP (natural language): create calendar table, treat data, build star schema,
   create all DAX measures.
3. Save as PBIX → then **Save as PBIP** (folder). Close Power BI Desktop.

**Phase 2 — Visuals, analysis and docs (Desktop closed + this MCP)**

4. `open_project` → analyze the PBIP project and the model built in Phase 1.
5. `create_page` + `create_visual` → generate **native Power BI pages and KPIs** from the
   existing measures, in natural language.
6. `analyze_data_quality` + `generate_documentation` → quality check and full documentation.
7. `convert_to_pbix` → deliver a complete, functional PBIX.

Every write step creates an automatic backup first. Result: a production-ready PBIX with
model + visuals + documentation, built entirely through natural language across two MCPs.

## Installation

### Requirements
- Python 3.10+
- Up-to-date `pip`
- Power BI Desktop or `pbi-tools` only if you need PBIP→PBIX conversion

### Automated install (Windows)
```powershell
.\install.ps1          # runtime
.\install.ps1 -Dev     # with dev dependencies
```
The installer creates `.venv`, installs dependencies, generates `.env` from `.env.example`
and verifies the server.

### Manual install
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .          # or:  pip install -e ".[dev]"
python -m powerbi_mcp --version
```

## Configuration

Configuration loads from environment variables or an `.env` file, prefixed with `PBIMCP_`.

| Variable | Purpose |
|---|---|
| `PBIMCP_LOG_LEVEL` | Log level (`INFO`, `DEBUG`, `WARNING`, …) |
| `PBIMCP_LOG_DIR` | Log directory |
| `PBIMCP_BACKUP_ENABLED` | Enable/disable automatic backups |
| `PBIMCP_BACKUP_DIR` | Backup directory |
| `PBIMCP_BACKUP_MAX` | Max backups per source |
| `PBIMCP_BACKUP_ENCRYPT` | Encrypt backups with Fernet when `true` |
| `PBIMCP_SECRET_KEY` | Fernet key for encryption |
| `PBIMCP_SURROGATE_SALT` | Salt for deterministic surrogate keys |
| `PBIMCP_AZURE_TENANT_ID` | Azure AD tenant |
| `PBIMCP_AZURE_CLIENT_ID` | Registered app client ID |
| `PBIMCP_AZURE_CLIENT_SECRET` | Client secret (service principal) |

Ready-to-use MCP client configs are in [clients/](clients/).

## Security Notes

- Every relevant write performs an **automatic backup** first.
- Restore validates the backup and supports files and folders.
- ZIP/PBIX extraction validates internal paths before writing (zip-slip protection).
- Writes are **atomic** where applicable.
- `dry_run` mode previews changes without persisting or leaving session residue.
- The **audit log** records model, project, visual, documentation, backup, restore and
  Power BI API operations.
- Secrets come from the environment or `.env`; `.env`, backups, logs and Power BI binaries
  are excluded via `.gitignore`.

See [SECURITY.md](SECURITY.md) for the disclosure policy.

> **Commercial use notice:** using this software in proprietary products or SaaS without
> publishing your source code under AGPL requires a commercial license. See [LEGAL.md](LEGAL.md).

## Quality & Testing

```powershell
python -m ruff check .
python -m mypy src
python -m pytest -q
python scripts\count_tools.py   # verify the tool count (66)
```

Verified reference results (real execution, not estimated):

- **362 automated tests** collected, covering project/session, model & DAX, AI/ML, HTML
  visuals, data quality, PII masking, encryption, Power BI REST API (mocked) and OAuth2.
- **~55% real coverage** (measured with `pytest --cov`).
- `ruff` and `mypy`: clean. `pip check`: no broken dependencies.
- A `tests/test_manifest_consistency.py` suite keeps `mcp-manifest.json` in sync with the
  real registered tools.

> **Transparency note:** earlier versions of this README reported unverified coverage
> figures. They were replaced with real results from running the full suite.

## Roadmap

- Incremental TMDL editing (edit only changed files instead of regenerating the model) to
  fully preserve complex metadata.
- Higher test coverage (target ≥ 70%).
- Optional PyPI distribution.

## Professional Portfolio Positioning

This repository is also a portfolio piece demonstrating:

- **Applied AI + BI**: real ML (forecasting, anomaly detection, clustering, RFM) wired into
  a Power BI workflow via the emerging MCP standard.
- **Software engineering**: modular architecture, typed Pydantic models, domain exceptions,
  automated backups/audit, and a real test suite with `ruff` + `mypy` in CI.
- **Security & governance awareness**: PII masking, encryption, audit logging and safe
  file handling by design.
- **Interoperability thinking**: designed to orchestrate alongside Microsoft's official MCP
  rather than compete with it.

## Development

```powershell
pip install -e ".[dev]"
python -m ruff check .
python -m mypy src
python -m pytest -q
```

## License

This project uses a **dual-licensing** model:

| Use | License |
|-----|---------|
| Personal, educational, open source (AGPL-compatible) | ✅ **Free** — [AGPL v3](LICENSE) |
| Commercial, SaaS, private/enterprise product | 💰 **Commercial License** — [terms](COMMERCIAL_LICENSE.md) |

- **AGPL v3 — free use:** if you use this software in an AGPL-compatible open-source project,
  it is completely free. See [LICENSE](LICENSE).
- **Commercial License:** if you integrate it into private products, SaaS or enterprise tools
  without publishing your source code, you need a commercial license.

📧 **Contact:** jeyssonzerpa@gmail.com · 📄 [COMMERCIAL_LICENSE.md](COMMERCIAL_LICENSE.md)

## Built With

Designed and developed by **Jeysson Zerpa** using a multi-agent, multi-IDE, AI-assisted
workflow:

| Tool | Role |
|------|------|
| **Claude (Anthropic)** | Architecture, code generation, auditing, refactoring, DevOps |
| **Cursor** | AI-assisted development and completion |
| **VS Code** | Primary editor and workspace management |
| **OpenCode** | AI terminal coding assistant |
| **Antigravity** | AI development support |

> All code, design decisions and project direction were driven by **Jeysson Zerpa**. AI tools
> were used as coding assistants under his supervision and review.

## Contact

- 💬 **WhatsApp:** [+55 (35) 99888-9882](https://wa.me/5535998889882) — fastest way
- 🐛 **Issues:** [report bugs or suggest improvements](https://github.com/jeyssonlza/powerbi-mcp-server/issues)

## Disclaimer

> **Power BI MCP Server is an independent open-source project and is NOT affiliated with,
> endorsed by, or sponsored by Microsoft Corporation.**
>
> "Power BI" is a registered trademark of Microsoft Corporation. This project uses the name
> solely to describe interoperability with Microsoft Power BI products.
>
> Use of the Power BI REST API is subject to
> [Microsoft's Terms of Service](https://learn.microsoft.com/en-us/rest/api/power-bi/). This
> tool does not redistribute any Microsoft software or proprietary code.
