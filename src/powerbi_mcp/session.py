"""Estado de sesión del servidor: proyecto PBIP activo.

Para evitar recargar el proyecto desde disco en cada herramienta, el servidor
mantiene un proyecto "activo" en memoria. Las herramientas de exploración leen
de él y las de modificación lo mutan; al guardar, se persiste con respaldo
automático y se registran auditoría y changelog.

Como cada proceso del servidor MCP atiende a un cliente (transporte stdio), un
estado a nivel de proceso es suficiente y seguro.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from powerbi_mcp.core.exceptions import PBIPNotFoundError
from powerbi_mcp.core.logger import get_logger
from powerbi_mcp.pbip.models import PbipProject, SemanticModel
from powerbi_mcp.pbip.reader import load_project

logger = get_logger(__name__)


class ProjectSession:
    """Mantiene el proyecto PBIP actualmente abierto en el servidor."""

    def __init__(self) -> None:
        self._project: PbipProject | None = None

    @property
    def is_open(self) -> bool:
        """True si hay un proyecto cargado."""
        return self._project is not None

    def open(self, path: str | Path, *, load_report: bool = True) -> PbipProject:
        """Carga un proyecto y lo establece como activo.

        Args:
            path: Carpeta raíz del proyecto o archivo ``.pbip``.
            load_report: Si se debe cargar también el reporte.

        Returns:
            El proyecto cargado.
        """
        self._project = load_project(path, load_report=load_report)
        logger.info("Proyecto activo: %s", self._project.name)
        return self._project

    def require(self) -> PbipProject:
        """Devuelve el proyecto activo o lanza error si no hay ninguno.

        Returns:
            El proyecto activo.

        Raises:
            PBIPNotFoundError: Si no hay proyecto abierto.
        """
        if self._project is None:
            raise PBIPNotFoundError(
                "No hay ningún proyecto abierto. Usa 'open_project' primero."
            )
        return self._project

    def require_semantic_model(self) -> SemanticModel:
        """Devuelve el modelo semántico del proyecto activo.

        Returns:
            El modelo semántico cargado.

        Raises:
            PBIPNotFoundError: Si no hay proyecto abierto o no tiene modelo.
        """
        project = self.require()
        if project.semantic_model is None:
            raise PBIPNotFoundError(
                "El proyecto activo no tiene modelo semántico cargado.",
                details={"project": project.name},
            )
        return project.semantic_model

    def reload(self) -> PbipProject:
        """Recarga el proyecto activo desde disco (descarta cambios en memoria).

        Returns:
            El proyecto recargado.
        """
        project = self.require()
        return self.open(project.root_path)

    def close(self) -> None:
        """Cierra el proyecto activo."""
        self._project = None

    def info(self) -> dict[str, Any]:
        """Devuelve un resumen del estado de la sesión.

        Returns:
            Diccionario con el estado (abierto/cerrado) y el resumen del proyecto.
        """
        if self._project is None:
            return {"open": False}
        return {"open": True, **self._project.summary()}


#: Sesión global compartida por todas las herramientas del proceso.
session = ProjectSession()


__all__ = ["ProjectSession", "SemanticModel", "session"]
