"""Registro de auditoría de operaciones del servidor.

Cada operación relevante (sobre todo las de escritura) se registra de forma
**append-only** en un archivo JSON Lines (``audit.log.jsonl``), capturando:

- Marca de tiempo (UTC).
- Actor/origen de la operación.
- Acción y objetivo.
- Resultado (éxito/error) y detalles.

Esto proporciona trazabilidad ("quién, qué, cuándo") y soporta consultas
posteriores para revisión de seguridad o cumplimiento.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from powerbi_mcp.config import Settings, get_settings
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

#: Nombre del archivo de auditoría (dentro del directorio de logs).
AUDIT_FILE = "audit.log.jsonl"


class AuditLogger:
    """Escribe y consulta el registro de auditoría.

    Args:
        settings: Configuración a usar. Si es ``None``, se toma la global.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.settings.log_dir.mkdir(parents=True, exist_ok=True)
        self.audit_path = self.settings.log_dir / AUDIT_FILE

    def record(
        self,
        action: str,
        *,
        target: str = "",
        actor: str = "mcp-client",
        status: str = "success",
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Registra una entrada de auditoría.

        Args:
            action: Acción realizada (ej. ``"add_measure"``).
            target: Objetivo de la acción (proyecto/objeto afectado).
            actor: Quién/qué originó la acción.
            status: ``"success"`` o ``"error"``.
            details: Detalles adicionales JSON-serializables.

        Returns:
            La entrada de auditoría registrada.
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "action": action,
            "target": target,
            "status": status,
            "details": details or {},
        }
        try:
            with self.audit_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError as exc:  # pragma: no cover
            logger.warning("No se pudo escribir el registro de auditoría: %s", exc)
        return entry

    def query(
        self,
        *,
        action: str | None = None,
        actor: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Consulta el registro de auditoría con filtros opcionales.

        Args:
            action: Filtra por acción exacta.
            actor: Filtra por actor exacto.
            status: Filtra por estado (``success``/``error``).
            limit: Máximo de entradas a devolver (las más recientes).

        Returns:
            Lista de entradas que cumplen los filtros, de la más reciente a la
            más antigua.
        """
        entries = self._read_all()
        if action:
            entries = [e for e in entries if e.get("action") == action]
        if actor:
            entries = [e for e in entries if e.get("actor") == actor]
        if status:
            entries = [e for e in entries if e.get("status") == status]
        entries.sort(key=lambda e: str(e.get("timestamp", "")), reverse=True)
        return entries[:limit]

    def summary(self) -> dict[str, Any]:
        """Devuelve un resumen agregado del registro de auditoría.

        Returns:
            Diccionario con totales por acción y por estado.
        """
        entries = self._read_all()
        by_action: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for e in entries:
            by_action[e.get("action", "?")] = by_action.get(e.get("action", "?"), 0) + 1
            by_status[e.get("status", "?")] = by_status.get(e.get("status", "?"), 0) + 1
        return {
            "total_entries": len(entries),
            "by_action": by_action,
            "by_status": by_status,
        }

    def _read_all(self) -> list[dict[str, Any]]:
        """Lee todas las entradas del archivo de auditoría."""
        if not self.audit_path.exists():
            return []
        entries: list[dict[str, Any]] = []
        try:
            with self.audit_path.open("r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError as exc:  # pragma: no cover
            logger.warning("No se pudo leer el registro de auditoría: %s", exc)
        return entries


#: Instancia perezosa compartida.
_default_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Devuelve la instancia compartida de :class:`AuditLogger`.

    Returns:
        El logger de auditoría global.
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = AuditLogger()
    return _default_logger


def audit(action: str, **kwargs: Any) -> dict[str, Any]:
    """Atajo para registrar una entrada usando el logger compartido.

    Args:
        action: Acción a registrar.
        **kwargs: Argumentos pasados a :meth:`AuditLogger.record`.

    Returns:
        La entrada de auditoría registrada.
    """
    return get_audit_logger().record(action, **kwargs)


__all__ = [
    "AUDIT_FILE",
    "AuditLogger",
    "audit",
    "get_audit_logger",
]
