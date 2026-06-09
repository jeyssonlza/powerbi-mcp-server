# Power BI MCP Server

<div align="center">

**Professional Model Context Protocol server for Power BI automation**

[![PyPI version](https://badge.fury.io/py/powerbi-mcp-server.svg)](https://badge.fury.io/py/powerbi-mcp-server)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![CI](https://github.com/jeyssonlza/powerbi-mcp-server/actions/workflows/ci.yml/badge.svg)](https://github.com/jeyssonlza/powerbi-mcp-server/actions/workflows/ci.yml)

</div>

---

## What is Power BI MCP Server?

The **Power BI MCP Server** gives AI assistants (Claude, GPT-4, etc.) direct, structured access to your Power BI projects through **67 specialized tools** organized in 8 domains.

Instead of copy-pasting DAX, you ask your AI:

> *"Create a revenue measure with time intelligence for the last 12 months"*

…and it calls the right MCP tool automatically.

---

## 67 Tools across 8 Domains

| Domain | Tools | Description |
|--------|-------|-------------|
| 🗂️ **Project** | 11 | Create, read, backup, export PBIP/PBIX projects |
| 📊 **Model** | 23 | Tables, columns, measures, relationships, DAX |
| 🤖 **AI & ML** | 8 | Anomaly detection, clustering, forecasting, RFM |
| 🎨 **Visuals** | 7 | Pages, charts, tables, themes, HTML export |
| 🔍 **Analysis** | 5 | Data quality, profiling, pattern detection |
| 📝 **Docs** | 3 | Markdown, HTML, data dictionary generation |
| 🔒 **Security** | 6 | PII masking, encryption, audit log, backup |
| ☁️ **Power BI API** | 5 | Workspaces, datasets, DAX queries, refresh |

---

## Quick Start

### Install

```bash
pip install powerbi-mcp-server
```

### Configure Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "powerbi": {
      "command": "powerbi-mcp",
      "env": {
        "POWERBI_TENANT_ID": "your-tenant-id",
        "POWERBI_CLIENT_ID": "your-client-id",
        "POWERBI_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Or run with Docker

```bash
docker compose up -d
```

---

## Example Usage

```python
# Ask your AI assistant:
"Create a table called Sales with columns: Date, Amount, ProductID"

# The MCP server calls automatically:
table_create(project_id="my-report", table_name="Sales", columns=[...])

# AI detects anomalies in your data:
ai_detect_anomalies(df=sales_data, method="isolation_forest")

# Generate documentation:
docs_generate_markdown(project_id="my-report", output_path="./docs/")
```

---

## Architecture

```
powerbi-mcp-server/
├── src/powerbi_mcp/
│   ├── server.py              # MCP orchestrator (182 lines)
│   ├── tools/
│   │   ├── project_tools.py   # 11 tools
│   │   ├── model_tools.py     # 23 tools
│   │   ├── ai_tools.py        # 8 tools
│   │   ├── visuals_tools.py   # 7 tools
│   │   ├── analysis_tools.py  # 5 tools
│   │   ├── docs_tools.py      # 3 tools
│   │   ├── security_tools.py  # 6 tools
│   │   └── pbi_api_tools.py   # 5 tools
│   └── pbip/                  # PBIP/PBIX format handlers
├── tests/                     # 32 test files, 5,873 LOC
├── Dockerfile
└── docker-compose.yml
```

---

## Requirements

- Python 3.10+
- Power BI Desktop (for local PBIP projects)
- Azure AD app registration (for Power BI Service API)
