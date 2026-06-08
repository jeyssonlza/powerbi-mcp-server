"""Herramientas para generación de documentación.

3 herramientas:
- generate_documentation, generate_data_dictionary, get_changelog
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.session import session


def _tool(func):
    """Decorador: captura errores del dominio y los devuelve estructurados."""
    import functools
    from powerbi_mcp.core.exceptions import PowerBIMCPError
    from powerbi_mcp.core.logger import get_logger

    logger = get_logger(__name__)

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PowerBIMCPError as exc:
            logger.warning("Error en '%s': %s", func.__name__, exc)
            return {"ok": False, **exc.to_dict()}
        except Exception as exc:
            logger.exception("Error inesperado en '%s'", func.__name__)
            return {
                "ok": False,
                "error": exc.__class__.__name__,
                "code": "unexpected_error",
                "message": str(exc),
            }

    return wrapper


def _audit_action(
    action: str,
    *,
    target: str = "",
    status: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Registra auditoria sin acoplar cada herramienta al logger concreto."""
    from powerbi_mcp.security.audit import audit

    audit(action, target=target, status=status, details=details)


def register_docs_tools(mcp) -> None:
    """Registra todas las herramientas de documentación en la instancia MCP."""

    @mcp.tool()
    @_tool
    def generate_documentation(
        output_dir: str | None = None,
        formats: list[str] | None = None,
        include_best_practices: bool = True,
    ) -> dict[str, Any]:
        """Genera la documentación técnica del proyecto activo.

        Args:
            output_dir: Carpeta de salida. Si es ``None``, devuelve el contenido.
            formats: Formatos a generar ('markdown', 'html'). Por defecto ambos.
            include_best_practices: Si incluye el análisis BPA.

        Returns:
            Contenido generado y/o rutas escritas.
        """
        from powerbi_mcp.docs.generator import generate_documentation as _gen

        project = session.require()
        result = _gen(
            project,
            output_dir=output_dir,
            formats=formats,
            include_best_practices=include_best_practices,
        )
        if output_dir:
            _audit_action(
                "generate_documentation",
                target=str(output_dir),
                details={"formats": result.get("formats")},
            )
        return {"ok": True, **result}

    @mcp.tool()
    @_tool
    def generate_data_dictionary(output_format: str = "markdown", output_path: str | None = None) -> dict[str, Any]:
        """Genera el diccionario de datos del modelo activo.

        Args:
            output_format: 'markdown', 'json' o 'csv'.
            output_path: Ruta donde guardar (opcional).

        Returns:
            El diccionario de datos en el formato solicitado.
        """
        from pathlib import Path

        from powerbi_mcp.docs.data_dictionary import (
            build_data_dictionary,
            dictionary_to_csv,
            dictionary_to_markdown,
        )

        model = session.require_semantic_model()
        dictionary = build_data_dictionary(model)

        if output_format == "markdown":
            content: Any = dictionary_to_markdown(dictionary)
        elif output_format == "csv":
            content = dictionary_to_csv(dictionary, "columns")
        else:
            content = dictionary

        result: dict[str, Any] = {"ok": True, "format": output_format, "content": content}
        if output_path:
            path = Path(output_path).expanduser().resolve()
            path.parent.mkdir(parents=True, exist_ok=True)
            text = content if isinstance(content, str) else __import__("json").dumps(content, indent=2, ensure_ascii=False)
            path.write_text(text, encoding="utf-8")
            result["path"] = str(path)
            _audit_action(
                "generate_data_dictionary",
                target=str(path),
                details={"format": output_format},
            )
        return result

    @mcp.tool()
    @_tool
    def get_changelog(output_format: str = "markdown") -> dict[str, Any]:
        """Devuelve el changelog automático del proyecto activo.

        Args:
            output_format: 'markdown' o 'json'.

        Returns:
            El changelog del proyecto.
        """
        from powerbi_mcp.docs.changelog import get_history, render_markdown

        project = session.require()
        if output_format == "json":
            return {"ok": True, "history": get_history(project.root_path)}
        return {"ok": True, "markdown": render_markdown(project.root_path, project_name=project.name)}
