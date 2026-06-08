# Configuracion De Clientes MCP

Esta carpeta incluye configuraciones iniciales para conectar Power BI MCP Server
con clientes compatibles con Model Context Protocol.

El servidor se ejecuta por transporte `stdio` usando:

```powershell
python -m powerbi_mcp
```

Cuando se usa entorno virtual, es recomendable apuntar el cliente al interprete
Python de `.venv`.

Ruta local preparada en este workspace:

```text
C:\Users\jeyss\Desktop\mcp visual PBI\.venv\Scripts\python.exe
```

Si el proyecto se mueve a otra carpeta o maquina, actualiza esa ruta en los
archivos de configuracion.

## Archivos Incluidos

| Archivo | Cliente |
|---|---|
| `claude_desktop_config.json` | Claude Desktop / Claude Code |
| `vscode_mcp.json` | VS Code / extensiones MCP |
| `mcp_servers.json` | Clientes con formato MCP estandar |
| `codex_config.toml` | Codex |
| `opencode.json` | OpenCode |

## Claude Desktop

Archivo de configuracion habitual:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

Usa el contenido de:

```text
clients\claude_desktop_config.json
```

Verifica que `command` apunte al Python correcto.

## Claude Code

Ejemplo desde la raiz del proyecto:

```powershell
claude mcp add powerbi --scope user -- "C:\Users\jeyss\Desktop\mcp visual PBI\.venv\Scripts\python.exe" -m powerbi_mcp
```

## VS Code

Copia o adapta:

```text
clients\vscode_mcp.json
```

Destino habitual dentro del workspace:

```text
.vscode\mcp.json
```

## Codex

Codex usa TOML. Agrega la seccion de:

```text
clients\codex_config.toml
```

al archivo:

```text
~\.codex\config.toml
```

## OpenCode

Usa el contenido de:

```text
clients\opencode.json
```

en la configuracion `opencode.json`, bajo la clave `mcp`.

## Verificacion

Antes de abrir el cliente, valida que el servidor inicia:

```powershell
& "C:\Users\jeyss\Desktop\mcp visual PBI\.venv\Scripts\python.exe" -m powerbi_mcp --version
```

Resultado esperado:

```text
powerbi-mcp 0.1.0
```

Luego prueba desde el cliente:

```text
Abre el proyecto PBIP en C:\ruta\a\mi\proyecto y lista las tablas.
```

## Variables Recomendadas

```json
{
  "PBIMCP_LOG_LEVEL": "INFO"
}
```

Para seguridad avanzada:

```json
{
  "PBIMCP_BACKUP_ENCRYPT": "true",
  "PBIMCP_SECRET_KEY": "<clave-fernet>",
  "PBIMCP_SURROGATE_SALT": "<salt-largo-y-secreto>"
}
```

La clave Fernet puede generarse desde un cliente MCP con
`generate_encryption_key` o desde Python usando el modulo de seguridad del
proyecto.
