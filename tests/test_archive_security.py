"""Tests para seguridad de archivos ZIP (path traversal prevention)."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from powerbi_mcp.core.archive import safe_extract_zip, validate_zip_members


class TestZipSecurity:
    """Suite de tests para seguridad ZIP."""

    def test_validate_safe_members(self, tmp_path: Path) -> None:
        """Miembros seguros deben pasar validación."""
        members = ["data/file.txt", "config.json", "folder/subfolder/data.csv"]
        safe = validate_zip_members(members, tmp_path)

        assert safe == members

    def test_reject_absolute_paths(self, tmp_path: Path) -> None:
        """Rutas absolutas deben rechazarse."""
        with pytest.raises(ValueError, match="ruta absoluta"):
            validate_zip_members(["/etc/passwd"], tmp_path)

    def test_reject_parent_directory_traversal(self, tmp_path: Path) -> None:
        """Subida de directorio (..) debe rechazarse."""
        with pytest.raises(ValueError, match="subida de directorio"):
            validate_zip_members(["../../../etc/passwd"], tmp_path)

    def test_reject_drive_letters(self, tmp_path: Path) -> None:
        """Letras de unidad (Windows) deben rechazarse."""
        with pytest.raises(ValueError, match="letra de unidad"):
            validate_zip_members(["C:\\Windows\\System32"], tmp_path)

    def test_reject_empty_member(self, tmp_path: Path) -> None:
        """Miembros vacíos deben rechazarse."""
        with pytest.raises(ValueError, match="vacío"):
            validate_zip_members([""], tmp_path)

    def test_safe_extract_zip_basic(self, tmp_path: Path) -> None:
        """Extracción básica debe funcionar."""
        zip_path = tmp_path / "safe.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("data.txt", "content")
            zf.writestr("folder/file.json", '{"key": "value"}')

        dest = tmp_path / "extracted"
        dest.mkdir()

        with zipfile.ZipFile(zip_path) as zf:
            extracted = safe_extract_zip(zf, dest)

        assert len(extracted) == 2
        assert (dest / "data.txt").exists()
        assert (dest / "folder" / "file.json").exists()

    def test_safe_extract_rejects_traversal(self, tmp_path: Path) -> None:
        """Extracción con traversal debe fallar."""
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("safe.txt", "ok")
            zf.writestr("../../../evil.txt", "pwned")

        dest = tmp_path / "extracted"
        dest.mkdir()

        with zipfile.ZipFile(zip_path) as zf, pytest.raises(ValueError):
            safe_extract_zip(zf, dest)

        # Evil file no debe existir fuera de destino
        assert not (tmp_path / "evil.txt").exists()

    def test_safe_extract_with_member_list(self, tmp_path: Path) -> None:
        """Debe aceptar lista específica de miembros a extraer."""
        zip_path = tmp_path / "multi.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file1.txt", "1")
            zf.writestr("file2.txt", "2")
            zf.writestr("file3.txt", "3")

        dest = tmp_path / "extracted"
        dest.mkdir()

        with zipfile.ZipFile(zip_path) as zf:
            safe_extract_zip(zf, dest, members=["file1.txt", "file3.txt"])

        assert (dest / "file1.txt").exists()
        assert not (dest / "file2.txt").exists()
        assert (dest / "file3.txt").exists()

    def test_safe_extract_preserves_directory_structure(self, tmp_path: Path) -> None:
        """Debe preservar estructura de directorios."""
        zip_path = tmp_path / "struct.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("a/b/c/deep.txt", "nested")

        dest = tmp_path / "extracted"
        dest.mkdir()

        with zipfile.ZipFile(zip_path) as zf:
            safe_extract_zip(zf, dest)

        assert (dest / "a" / "b" / "c" / "deep.txt").exists()
        assert (dest / "a" / "b" / "c" / "deep.txt").read_text() == "nested"

    def test_backslashes_are_accepted_as_safe(self, tmp_path: Path) -> None:
        """Un miembro con backslashes (no es path traversal) debe aceptarse.

        La validación normaliza los separadores internamente para comprobar la
        seguridad, pero devuelve el nombre original sin alterar (así
        ``zipfile.extractall(members=...)`` puede localizarlo en el ZIP).
        """
        members = ["folder\\subfolder\\file.txt"]
        safe = validate_zip_members(members, tmp_path)

        assert len(safe) == 1
        # El nombre se devuelve tal cual (sin transformar) para extractall.
        assert safe[0] == "folder\\subfolder\\file.txt"

    def test_multiple_dangerous_patterns(self, tmp_path: Path) -> None:
        """Múltiples patrones peligrosos deben detectarse."""
        dangerous = [
            "../file.txt",
            "../../file.txt",
            "/../sensitive.txt",
            "/abs/path.txt",
            "C:\\windows\\file.txt",
            "D:\\data\\file.txt",
        ]

        for bad in dangerous:
            with pytest.raises(ValueError):
                validate_zip_members([bad], tmp_path)
