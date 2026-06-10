# Security Policy

## Supported Version

This project is in its initial public-ready stage. Security fixes are expected
to target the latest version published in the main branch.

| Version | Supported |
|---|---|
| `0.1.x` | Yes |

## Reporting A Vulnerability

If you discover a vulnerability, please report it privately before opening a
public issue.

Preferred channel:

- Email: `jeyssonzerpa@gmail.com`

Please include:

- A clear description of the issue.
- Steps to reproduce it.
- The affected version or commit.
- Whether real Power BI files, credentials or customer data are involved.
- Any suggested mitigation, if available.

## Security Scope

The project includes controls for:

- Safe ZIP/PBIX extraction.
- Backup and restore validation.
- Optional encrypted backups.
- Audit logs for relevant operations.
- Secret loading through environment variables or `.env`.
- `.gitignore` exclusions for local secrets, logs, backups and generated files.

## Important Notice

The internal technical audit is not a replacement for legal review, compliance
certification, penetration testing, SOC, ISO, PCI or enterprise security
approval. Regulated environments should perform their own external review before
production use.
