# Contributing

Thank you for considering a contribution to Power BI MCP Server.

This project is designed to be safe, auditable and practical for Power BI
automation. Contributions should preserve those goals.

## Development Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

On Linux or macOS:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Verification

Before submitting changes, run:

```powershell
python -m pip check
python -m pytest -q
python tests\smoke_e2e.py
```

If development dependencies are installed and the codebase is ready for stricter
checks, also run:

```powershell
python -m ruff check .
python -m mypy src
```

## Contribution Guidelines

- Do not commit `.env`, credentials, tokens, backups, logs or private PBIX/PBIP
  files.
- Add or update tests for behavior changes.
- Keep documentation aligned with implemented behavior.
- Prefer small, focused pull requests.
- Preserve safe file handling for ZIP/PBIX operations.
- Use `dry_run` behavior carefully; it must not persist changes or leave stale
  session state.
- Do not remove audit logging from write, restore, documentation or API actions.

## Pull Request Checklist

- Tests pass locally.
- Documentation was updated when behavior changed.
- No generated artifacts are included.
- No secrets or customer data are included.
- Security-sensitive changes include a short explanation of the risk and
  mitigation.
