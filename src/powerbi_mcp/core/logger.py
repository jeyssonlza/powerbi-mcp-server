"""Configuración de logging del servidor Power BI MCP.

Particularidad crítica de MCP por **stdio**: ``stdout`` está reservado para el
protocolo JSON-RPC. Escribir logs en ``stdout`` corrompería la comunicación.
Por eso todos los handlers de consola escriben en **stderr**, y adicionalmente
se persiste un archivo de log **rotativo** en disco.

Uso::

    from powerbi_mcp.core.logger import get_logger, setup_logging

    setup_logging()              # una sola vez al arrancar el servidor
    log = get_logger(__name__)
    log.info("Proyecto abierto", extra={"path": str(path)})
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from powerbi_mcp.config import Settings, get_settings

#: Nombre del logger raíz del paquete. Todos los loggers cuelgan de aquí.
ROOT_LOGGER_NAME = "powerbi_mcp"

#: Formato detallado para el archivo de log.
_FILE_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(funcName)s:%(lineno)d | %(message)s"
)

#: Bandera interna para no configurar el logging más de una vez.
_configured = False


def setup_logging(settings: Settings | None = None, *, force: bool = False) -> logging.Logger:
    """Configura el logging global del servidor (consola en stderr + archivo).

    Es idempotente: llamarla varias veces no duplica handlers salvo que se pase
    ``force=True``.

    Args:
        settings: Configuración a usar. Si es ``None`` se obtiene de
            :func:`~powerbi_mcp.config.get_settings`.
        force: Si es ``True``, reinstala los handlers aunque ya estuvieran
            configurados (útil en tests).

    Returns:
        El logger raíz del paquete (``powerbi_mcp``).
    """
    global _configured
    settings = settings or get_settings()

    logger = logging.getLogger(ROOT_LOGGER_NAME)

    if _configured and not force:
        return logger

    logger.setLevel(settings.log_level)
    logger.handlers.clear()
    # Evita que los mensajes suban al root logger global (y a stdout).
    logger.propagate = False

    # --- Handler de consola -> SIEMPRE stderr ------------------------------
    console_handler = logging.StreamHandler(stream=sys.stderr)
    console_handler.setLevel(settings.log_level)
    console_handler.setFormatter(_build_console_formatter())
    logger.addHandler(console_handler)

    # --- Handler de archivo rotativo ---------------------------------------
    try:
        settings.log_dir.mkdir(parents=True, exist_ok=True)
        file_path: Path = settings.log_dir / "powerbi_mcp.log"
        file_handler = RotatingFileHandler(
            file_path,
            maxBytes=5 * 1024 * 1024,  # 5 MB por archivo
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # el archivo guarda todo el detalle
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
        logger.addHandler(file_handler)
    except OSError as exc:  # pragma: no cover - depende del entorno de archivos
        # Si no se puede escribir el archivo, seguimos solo con consola.
        logger.warning("No se pudo inicializar el log de archivo: %s", exc)

    _configured = True
    logger.debug("Logging inicializado (nivel=%s)", settings.log_level)
    return logger


def _build_console_formatter() -> logging.Formatter:
    """Crea el formateador de consola, usando ``rich`` si está disponible.

    Returns:
        Un :class:`logging.Formatter` legible para la consola (stderr).
    """
    # rich es opcional; si no está, usamos un formato plano simple.
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )


def get_logger(name: str | None = None) -> logging.Logger:
    """Devuelve un logger hijo del logger raíz del paquete.

    Args:
        name: Nombre del módulo (normalmente ``__name__``). Si es ``None`` o ya
            pertenece al árbol ``powerbi_mcp``, se devuelve el logger adecuado.

    Returns:
        Un :class:`logging.Logger` correctamente anidado bajo ``powerbi_mcp``.
    """
    if not name or name == ROOT_LOGGER_NAME:
        return logging.getLogger(ROOT_LOGGER_NAME)
    if name.startswith(ROOT_LOGGER_NAME + "."):
        return logging.getLogger(name)
    # Anidar cualquier otro nombre bajo el logger raíz del paquete.
    short = name.rsplit(".", 1)[-1]
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{short}")


__all__ = ["ROOT_LOGGER_NAME", "get_logger", "setup_logging"]
