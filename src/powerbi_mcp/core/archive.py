"""Utilidades seguras para trabajar con archivos ZIP.

Implementa validación de ruta (path traversal prevention) siguiendo las
recomendaciones de OWASP para extracciones seguras de archivos.
"""

from __future__ import annotations

import zipfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath


def validate_zip_members(members: Iterable[str], destination: str | Path) -> list[str]:
    """Valida que los miembros de un ZIP no escapen del destino.

    Implementa protección contra path traversal attacks:
    - Rechaza rutas absolutas (ej: /etc/passwd)
    - Rechaza subidas de directorio (ej: ../)
    - Rechaza letras de unidad (ej: C:)
    - Valida que path.resolve() esté dentro del destino

    Args:
        members: Nombres internos del ZIP.
        destination: Carpeta base donde se extraerían.

    Returns:
        Lista de miembros válidos.

    Raises:
        ValueError: Si un miembro intenta escribir fuera del destino.

    Example:
        >>> safe = validate_zip_members(
        ...     ["data/file.txt", "config.json"],
        ...     destination="/tmp/extract"
        ... )
    """
    dest = Path(destination).expanduser().resolve()
    safe_members: list[str] = []

    for member in members:
        # Normalizar separadores
        normalized = member.replace("\\", "/")

        # Rechazar valores vacíos
        if not normalized or normalized == ".":
            raise ValueError(f"Miembro ZIP inválido (vacío o actual): {member}")

        # Rechazar rutas absolutas
        if normalized.startswith("/"):
            raise ValueError(f"Miembro ZIP con ruta absoluta: {member}")

        # Analizar partes para detectar ataques
        parts = PurePosixPath(normalized).parts

        # Rechazar subida de directorio (..)
        if ".." in parts:
            raise ValueError(f"Miembro ZIP con subida de directorio (..): {member}")

        # Rechazar letras de unidad (Windows: C:, D:, etc.)
        if parts and ":" in parts[0]:
            raise ValueError(f"Miembro ZIP con letra de unidad: {member}")

        # Validar con Path.resolve() que la ruta final está dentro del destino
        target = (dest / normalized).resolve()

        # Comparar inode o string (según plataforma)
        try:
            if not target.relative_to(dest):
                # La ruta está dentro del destino
                pass
        except ValueError:
            # relative_to() falla si target no está bajo dest
            raise ValueError(
                f"Miembro ZIP escapa del destino: {member} -> {target}"
            ) from None

        safe_members.append(member)

    return safe_members


def safe_extract_zip(
    zf: zipfile.ZipFile,
    destination: str | Path,
    *,
    members: Iterable[str] | None = None,
) -> list[str]:
    """Extrae un archivo ZIP después de validar todas las rutas internas.

    Args:
        zf: Archivo ZIP abierto.
        destination: Carpeta destino.
        members: Miembros a extraer (todos si es None).

    Returns:
        Lista de miembros extraídos.

    Raises:
        ValueError: Si algún miembro es inseguro.

    Example:
        >>> import zipfile
        >>> with zipfile.ZipFile("archive.zip") as zf:
        ...     safe_extract_zip(zf, "/tmp/output")
    """
    selected = list(members) if members is not None else zf.namelist()
    safe_members = validate_zip_members(selected, destination)
    zf.extractall(destination, members=safe_members)
    return safe_members


__all__ = ["safe_extract_zip", "validate_zip_members"]
