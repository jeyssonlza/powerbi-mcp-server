"""Herramientas para gestión de proyectos Power BI (PBIP/PBIX).

11 herramientas:
- open_project, project_info, project_structure, reload_project, close_project
- list_backups, create_backup, restore_backup, convert_to_pbix, read_pbix_info
"""

from __future__ import annotations

from typing import Any

from powerbi_mcp.session import session


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


def _reload_after_write(dry_run: bool) -> None:
    """Mantiene la sesion sincronizada con disco tras escrituras PBIR."""
    if not dry_run:
        session.reload()


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


def register_project_tools(mcp) -> None:
    """Registra todas las herramientas de proyecto en la instancia MCP."""

    @mcp.tool()
    @_tool
    def open_project(path: str, load_report: bool = True) -> dict[str, Any]:
        """Abre un proyecto Power BI (PBIP) y lo establece como activo.

        Args:
            path: Carpeta raíz del proyecto o ruta a un archivo ``.pbip``.
            load_report: Si se debe cargar también el reporte (páginas/visuales).

        Returns:
            Resumen del proyecto cargado (tablas, medidas, relaciones, páginas...).
        """
        project = session.open(path, load_report=load_report)
        return {"ok": True, **project.summary()}

    @mcp.tool()
    @_tool
    def project_info() -> dict[str, Any]:
        """Devuelve información del proyecto actualmente abierto.

        Returns:
            Estado de la sesión y resumen del proyecto activo (si lo hay).
        """
        return {"ok": True, **session.info()}

    @mcp.tool()
    @_tool
    def project_structure(max_depth: int = 4) -> dict[str, Any]:
        """Devuelve el árbol de archivos y carpetas del proyecto activo.

        Args:
            max_depth: Profundidad máxima del árbol.

        Returns:
            Estructura jerárquica de archivos del proyecto.
        """
        from powerbi_mcp.pbip.parser import build_file_tree

        project = session.require()
        return {"ok": True, "tree": build_file_tree(project.root_path, max_depth=max_depth)}

    @mcp.tool()
    @_tool
    def reload_project() -> dict[str, Any]:
        """Recarga el proyecto activo desde disco, descartando cambios en memoria.

        Returns:
            Resumen del proyecto recargado.
        """
        project = session.reload()
        return {"ok": True, **project.summary()}

    @mcp.tool()
    @_tool
    def close_project() -> dict[str, Any]:
        """Cierra el proyecto activo.

        Returns:
            Confirmación del cierre.
        """
        session.close()
        return {"ok": True, "closed": True}

    @mcp.tool()
    @_tool
    def list_backups(source_name: str | None = None) -> dict[str, Any]:
        """Lista los respaldos disponibles.

        Args:
            source_name: Nombre del proyecto/archivo a filtrar (opcional).

        Returns:
            Lista de respaldos (del más reciente al más antiguo).
        """
        from powerbi_mcp.core.backup import BackupManager

        return {"ok": True, "backups": BackupManager().list_backups(source_name)}

    @mcp.tool()
    @_tool
    def create_backup(reason: str = "manual") -> dict[str, Any]:
        """Crea un respaldo manual del proyecto activo.

        Args:
            reason: Motivo del respaldo.

        Returns:
            Registro del respaldo creado.
        """
        from powerbi_mcp.core.backup import BackupManager

        project = session.require()
        record = BackupManager().create_backup(project.root_path, reason=reason)
        _audit_action(
            "create_backup",
            target=project.name,
            details={"reason": reason, "backup_id": record.backup_id if record else None},
        )
        return {"ok": True, "backup": record.to_dict() if record else None}

    @mcp.tool()
    @_tool
    def restore_backup(backup_id: str, dry_run: bool = False) -> dict[str, Any]:
        """Restaura un respaldo por su identificador.

        Args:
            backup_id: Identificador del respaldo a restaurar.
            dry_run: Si es ``True``, previsualiza sin escribir.

        Returns:
            Ruta donde se restauró (o se restauraría) el contenido.
        """
        from powerbi_mcp.core.backup import BackupManager

        target = BackupManager().restore_backup(backup_id, dry_run=dry_run)
        if not dry_run and session.is_open:
            session.reload()
        _audit_action(
            "restore_backup",
            target=backup_id,
            details={"dry_run": dry_run, "restored_to": str(target)},
        )
        return {"ok": True, "restored_to": str(target), "dry_run": dry_run}

    @mcp.tool()
    @_tool
    def convert_to_pbix(output_path: str | None = None, overwrite: bool = False) -> dict[str, Any]:
        """Convierte el proyecto PBIP activo a un archivo PBIX (vía pbi-tools).

        Args:
            output_path: Ruta de salida del ``.pbix`` (opcional).
            overwrite: Si es ``True``, sobrescribe un PBIX existente.

        Returns:
            Estado de la conversión (``converted`` o ``manual_required``).
        """
        from powerbi_mcp.pbip.pbix import convert_pbip_to_pbix

        project = session.require()
        source = project.pbip_file or project.root_path
        result = convert_pbip_to_pbix(source, output_path, overwrite=overwrite)
        _audit_action(
            "convert_to_pbix",
            target=str(source),
            details={"status": result.get("status"), "output": result.get("output")},
        )
        return {"ok": True, **result}

    @mcp.tool()
    @_tool
    def read_pbix_info(pbix_path: str) -> dict[str, Any]:
        """Lee metadatos de un archivo PBIX existente.

        Args:
            pbix_path: Ruta del archivo ``.pbix``.

        Returns:
            Metadatos del PBIX (miembros, presencia de DataModel/Layout...).
        """
        from powerbi_mcp.pbip.pbix import pbix_info

        return {"ok": True, **pbix_info(pbix_path)}
