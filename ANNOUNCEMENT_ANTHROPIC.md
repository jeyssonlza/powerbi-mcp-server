# Anthropic Community Announcement — Power BI MCP Server v0.1.0

**Forum:** https://www.anthropic.com/community  
**Or:** https://github.com/orgs/modelcontextprotocol/discussions

---

## 📧 ANNOUNCEMENT TEMPLATE

**Subject:** [New MCP Server] Power BI MCP Server — 67 tools for PBIP/PBIX automation

---

Hi Anthropic & MCP community! 👋

I'm excited to share **Power BI MCP Server**, a professional-grade MCP server
that gives Claude (and other AI assistants) direct access to Power BI projects.

### 🚀 What it does

**67 tools** across 8 domains enabling AI-powered Power BI automation:

| Domain | Tools | Examples |
|--------|-------|---------|
| 🗂️ Project | 11 | Create, backup, export PBIP/PBIX |
| 📊 Model | 23 | Tables, columns, measures, DAX, relationships |
| 🤖 AI & ML | 8 | Anomaly detection, clustering, forecasting, RFM |
| 🎨 Visuals | 7 | Pages, charts, themes, HTML export |
| 🔍 Analysis | 5 | Data quality, profiling, pattern detection |
| 📝 Docs | 3 | Markdown, HTML, data dictionary |
| 🔒 Security | 6 | PII masking, encryption, audit log |
| ☁️ Power BI API | 5 | Workspaces, datasets, DAX queries, refresh |

### 💡 Example interaction

```
User → Claude: "Analyze sales data for anomalies and create a measure 
                for YoY growth with time intelligence"

Claude → MCP: ai_detect_anomalies(df=sales_data, method="isolation_forest")
         MCP: measure_create(name="Revenue YoY%", dax="DIVIDE(
                               [Revenue] - CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[Date])),
                               CALCULATE([Revenue], SAMEPERIODLASTYEAR('Date'[Date])))")
```

### 📦 Install

```bash
pip install powerbi-mcp-server
```

### 🔧 Configure Claude Desktop

```json
{
  "mcpServers": {
    "powerbi": {
      "command": "powerbi-mcp"
    }
  }
}
```

### 📚 Links

- **GitHub:** https://github.com/jeyssonzerpa/powerbi-mcp-server
- **PyPI:** https://pypi.org/project/powerbi-mcp-server/
- **Docs:** https://powerbi-mcp-server.readthedocs.io
- **Docker:** `docker compose up -d`

### 🏗️ Architecture highlights

- ✅ Modular architecture (8 specialized modules)
- ✅ Full Docker + CI/CD support
- ✅ OAuth2 authentication with Azure AD
- ✅ Enterprise-grade security (AES-256, audit trail)
- ✅ Python 3.10 → 3.14 compatibility

Would love feedback from the community! Questions welcome.

— Jeysson Zerpa
  jeyssonzerpa@gmail.com

---

## 📋 WHERE TO POST

### Option 1: Anthropic Discord
- Server: https://discord.gg/anthropic
- Channel: #mcp-servers or #community-projects

### Option 2: MCP GitHub Discussions
- URL: https://github.com/orgs/modelcontextprotocol/discussions
- Category: "Show and Tell"

### Option 3: Reddit r/ClaudeAI
- URL: https://www.reddit.com/r/ClaudeAI/
- Flair: "Project / Tool"

### Option 4: Awesome MCP Servers (PR)
- URL: https://github.com/punkpeye/awesome-mcp-servers
- Add entry: `powerbi-mcp-server` under "Data & Analytics"

### Option 5: MCP Registry Direct Submission
- URL: https://github.com/modelcontextprotocol/registry
- File: Submit mcp-manifest.json via PR
