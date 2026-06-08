"""Sistema de respaldo automático y restauración de proyectos PBIP.

Antes de **cualquier** operación de escritura, el servidor crea un respaldo
completo del archivo o proyecto afectado. Los respaldos:

- Se guardan como ``.zip`` con marca de tiempo y un manifiesto JSON.
- Se rotan automáticamente conservando los ``backup_max`` más recientes.
- Pueden encriptarse si ``backup_encrypt`` está activo y hay ``secret_key``.
- Pueden restaurarse de forma íntegra.

Ejemplo::

    from powerbi_mcp.core.backup import BackupManager

    mgr = BackupManager()
    record = mgr.create_backup(project_dir, reason="add_measure Ventas YoY")
    ...
    mgr.restore_backup(record.backup_id, target=project_dir)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from powerbi_mcp.config import Settings, get_settings
from powerbi_mcp.core.archive import safe_extract_zip, validate_zip_members
from powerbi_mcp.core.exceptions import BackupError, PowerBIMCPError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)

#: Nombre del manifiesto incluido dentro de cada respaldo.
_MANIFEST_NAME = "_backup_manifest.json"


@dataclass
class BackupRecord:
    """Metadatos de un respaldo creado.

    Attributes:
        backup_id: Identificador único (nombre de archivo sin extensión).
        source_path: Ruta original respaldada.
        backup_path: Ruta del archivo ``.zip`` generado.
        created_at: Marca de tiempo ISO-8601 (UTC) de creación.
        reason: Motivo/operación que disparó el respaldo.
        file_count: Número de archivos incluidos.
        size_bytes: Tamaño total del respaldo en bytes.
        encrypted: Si el contenido está encriptado.
    """

    backup_id: str
    source_path: str
    backup_path: str
    created_at: str
    reason: str
    file_count: int
    size_bytes: int
    encrypted: bool = False
    source_type: str = "unknown"

    def to_dict(self) -> dict[str, object]:
        """Serializa el registro a diccionario."""
        return asdict(self)


class BackupManager:
    """Gestiona la creación, listado, rotación y restauración de respaldos.

    Args:
        settings: Configuración a usar. Si es ``None`` se toma la global.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.backup_root = self.settings.backup_dir
        self.backup_root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ crear
    def create_backup(
        self,
        source: str | Path,
        *,
        reason: str = "",
        dry_run: bool = False,
    ) -> BackupRecord | None:
        """Crea un respaldo comprimido del archivo o directorio indicado.

        Args:
            source: Archivo o carpeta a respaldar.
            reason: Descripción de la operación que motiva el respaldo
                (se guarda en el manifiesto y en el log de auditoría).
            dry_run: Si es ``True``, no escribe nada y devuelve ``None``.

        Returns:
            El :class:`BackupRecord` del respaldo creado, o ``None`` si el
            respaldo está deshabilitado o en modo ``dry_run``.

        Raises:
            BackupError: Si la fuente no existe o falla la compresión.
        """
        if not self.settings.backup_enabled:
            logger.debug("Respaldo deshabilitado por configuración; se omite.")
            return None
        if dry_run:
            logger.info("[dry-run] Se habría respaldado %s (%s)", source, reason)
            return None

        src = Path(source).expanduser().resolve()
        if not src.exists():
            raise BackupError(
                "No se puede respaldar: la fuente no existe.",
                details={"source": str(src)},
            )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        backup_id = f"{src.name}__{timestamp}"
        project_backup_dir = self.backup_root / src.name
        project_backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = project_backup_dir / f"{backup_id}.zip"
        encrypted = False

        try:
            file_count = self._zip_source(src, backup_path)
            if self.settings.backup_encrypt:
                backup_path = self._encrypt_backup(backup_path)
                encrypted = True
        except (OSError, PowerBIMCPError) as exc:
            if backup_path.exists():
                backup_path.unlink(missing_ok=True)
            raise BackupError(
                "Fallo al crear el respaldo.",
                details={"source": str(src), "error": str(exc)},
            ) from exc

        record = BackupRecord(
            backup_id=backup_id,
            source_path=str(src),
            backup_path=str(backup_path),
            created_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            file_count=file_count,
            size_bytes=backup_path.stat().st_size,
            encrypted=encrypted,
            source_type="file" if src.is_file() else "directory",
        )

        self._write_manifest(project_backup_dir, record)
        logger.info(
            "Respaldo creado: %s (%d archivos, %d bytes) | motivo=%s",
            backup_id,
            file_count,
            record.size_bytes,
            reason,
        )

        self._rotate(project_backup_dir)
        return record

    def _zip_source(self, src: Path, backup_path: Path) -> int:
        """Comprime ``src`` (archivo o carpeta) en ``backup_path``.

        Returns:
            El número de archivos incluidos en el zip.
        """
        file_count = 0
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if src.is_file():
                zf.write(src, arcname=src.name)
                file_count = 1
            else:
                for item in src.rglob("*"):
                    if item.is_file():
                        # Excluir respaldos previos anidados, por si acaso.
                        if self.backup_root in item.parents:
                            continue
                        zf.write(item, arcname=str(item.relative_to(src)))
                        file_count += 1
        return file_count

    def _encrypt_backup(self, backup_path: Path) -> Path:
        """Encripta un ZIP de respaldo y elimina el archivo plano."""
        if not self.settings.secret_key:
            raise BackupError(
                "PBIMCP_BACKUP_ENCRYPT requiere PBIMCP_SECRET_KEY.",
                details={"backup": str(backup_path)},
            )

        from powerbi_mcp.security.encryption import Encryptor

        encrypted_path = backup_path.with_suffix(backup_path.suffix + ".enc")
        Encryptor(self.settings.secret_key).encrypt_file(backup_path, encrypted_path)
        backup_path.unlink(missing_ok=True)
        return encrypted_path

    def _write_manifest(self, project_backup_dir: Path, record: BackupRecord) -> None:
        """Actualiza el índice de respaldos del proyecto (manifiesto JSON)."""
        manifest_path = project_backup_dir / _MANIFEST_NAME
        records = self._read_manifest(project_backup_dir)
        records.append(record.to_dict())
        manifest_path.write_text(
            json.dumps(records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _read_manifest(self, project_backup_dir: Path) -> list[dict[str, object]]:
        """Lee el manifiesto de respaldos de un proyecto (lista, posiblemente vacía)."""
        manifest_path = project_backup_dir / _MANIFEST_NAME
        if not manifest_path.exists():
            return []
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            logger.warning("Manifiesto de respaldo corrupto en %s", project_backup_dir)
            return []

    # --------------------------------------------------------------- rotación
    def _rotate(self, project_backup_dir: Path) -> None:
        """Elimina los respaldos más antiguos si se supera ``backup_max``."""
        max_keep = self.settings.backup_max
        if max_keep <= 0:
            return

        backups = sorted(
            [*project_backup_dir.glob("*.zip"), *project_backup_dir.glob("*.zip.enc")],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in backups[max_keep:]:
            try:
                old.unlink()
                logger.debug("Respaldo rotado (eliminado): %s", old.name)
            except OSError as exc:  # pragma: no cover
                logger.warning("No se pudo eliminar respaldo antiguo %s: %s", old, exc)

    # ---------------------------------------------------------------- listar
    def list_backups(self, source_name: str | None = None) -> list[dict[str, object]]:
        """Lista los respaldos disponibles.

        Args:
            source_name: Nombre del proyecto/archivo a filtrar. Si es ``None``,
                lista los respaldos de todos los proyectos.

        Returns:
            Lista de registros de respaldo (diccionarios), del más reciente al
            más antiguo.
        """
        records: list[dict[str, object]] = []
        dirs = (
            [self.backup_root / source_name]
            if source_name
            else [d for d in self.backup_root.iterdir() if d.is_dir()]
        )
        for d in dirs:
            if d.exists():
                records.extend(self._read_manifest(d))
        records.sort(key=lambda r: str(r.get("created_at", "")), reverse=True)
        return records

    # ------------------------------------------------------------- restaurar
    def restore_backup(
        self,
        backup_id: str,
        *,
        target: str | Path | None = None,
        dry_run: bool = False,
    ) -> Path:
        """Restaura un respaldo a su ubicación original o a un destino dado.

        Antes de restaurar se crea un respaldo de seguridad del estado actual
        del destino (si existe), para no perder cambios no respaldados.

        Args:
            backup_id: Identificador del respaldo a restaurar.
            target: Carpeta/archivo destino. Si es ``None`` se usa la ruta
                original registrada en el respaldo.
            dry_run: Si es ``True``, valida pero no escribe; devuelve la ruta
                destino prevista.

        Returns:
            La ruta donde se restauró (o se restauraría) el contenido.

        Raises:
            BackupError: Si no se encuentra el respaldo o falla la extracción.
        """
        record = self._find_record(backup_id)
        backup_path = self._record_backup_path(record) or self._find_backup_file(backup_id)
        if backup_path is None:
            raise BackupError(
                "No se encontró el respaldo solicitado.",
                details={"backup_id": backup_id},
            )

        dest = Path(target).expanduser().resolve() if target else Path(str(record["source_path"]))

        if dry_run:
            logger.info("[dry-run] Se restauraría %s en %s", backup_id, dest)
            return dest

        # Respaldo de seguridad del estado actual antes de sobrescribir.
        if dest.exists():
            self.create_backup(dest, reason=f"pre-restore de {backup_id}")

        zip_path, temp_path = self._readable_backup_zip(backup_path, record)
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                members = [m for m in zf.namelist() if m != _MANIFEST_NAME]
                if self._is_file_backup(record, members):
                    self._restore_file(zf, members, dest)
                else:
                    if dest.exists() and not dest.is_dir():
                        raise BackupError(
                            "El destino existe y no es una carpeta.",
                            details={"destination": str(dest)},
                        )
                    dest.mkdir(parents=True, exist_ok=True)
                    safe_extract_zip(zf, dest, members=members)
        except (OSError, zipfile.BadZipFile, ValueError) as exc:
            raise BackupError(
                "Fallo al restaurar el respaldo.",
                details={"backup_id": backup_id, "error": str(exc)},
            ) from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

        logger.info("Respaldo %s restaurado en %s", backup_id, dest)
        return dest

    def _record_backup_path(self, record: dict[str, Any]) -> Path | None:
        """Devuelve la ruta de respaldo registrada si todavia existe."""
        raw_path = record.get("backup_path")
        if not raw_path:
            return None
        path = Path(str(raw_path)).expanduser().resolve()
        return path if path.exists() else None

    def _readable_backup_zip(
        self, backup_path: Path, record: dict[str, Any]
    ) -> tuple[Path, Path | None]:
        """Devuelve un ZIP legible, desencriptando a temporal si hace falta."""
        if not bool(record.get("encrypted")):
            return backup_path, None

        from powerbi_mcp.security.encryption import Encryptor

        fd, tmp_name = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        temp_path = Path(tmp_name)
        try:
            Encryptor(self.settings.secret_key).decrypt_file(backup_path, temp_path)
        except PowerBIMCPError:
            temp_path.unlink(missing_ok=True)
            raise
        return temp_path, temp_path

    def _is_file_backup(self, record: dict[str, Any], members: list[str]) -> bool:
        """Determina si el respaldo representa un unico archivo."""
        if record.get("source_type") == "file":
            return True
        source_name = Path(str(record.get("source_path", ""))).name
        return len(members) == 1 and Path(members[0]).name == source_name

    def _restore_file(self, zf: zipfile.ZipFile, members: list[str], dest: Path) -> None:
        """Restaura un respaldo de archivo de forma atomica."""
        if len(members) != 1:
            raise BackupError(
                "Un respaldo de archivo debe contener exactamente un archivo.",
                details={"members": members},
            )

        member = members[0]
        normalized = member.replace("\\", "/")
        validate_zip_members([normalized], dest.parent)
        if "/" in normalized.rstrip("/"):
            raise BackupError(
                "Ruta interna invalida para respaldo de archivo.",
                details={"member": member},
            )

        dest.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(dest.parent), suffix=".restore.tmp")
        try:
            with os.fdopen(fd, "wb") as fh, zf.open(member, "r") as source:
                shutil.copyfileobj(source, fh)
            os.replace(tmp_name, dest)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def _find_backup_file(self, backup_id: str) -> Path | None:
        """Busca el archivo de un respaldo por su identificador."""
        matches = [
            *self.backup_root.rglob(f"{backup_id}.zip"),
            *self.backup_root.rglob(f"{backup_id}.zip.enc"),
        ]
        return matches[0] if matches else None

    def _find_record(self, backup_id: str) -> dict[str, object]:
        """Busca el registro de manifiesto de un respaldo por su identificador.

        Raises:
            BackupError: Si no existe el registro.
        """
        for record in self.list_backups():
            if record.get("backup_id") == backup_id:
                return record
        raise BackupError(
            "No existe registro para el respaldo indicado.",
            details={"backup_id": backup_id},
        )


def auto_backup(source: str | Path, *, reason: str, dry_run: bool = False) -> BackupRecord | None:
    """Atajo para crear un respaldo con la configuración global.

    Pensada para llamarse desde las funciones de escritura justo antes de
    modificar disco.

    Args:
        source: Archivo o carpeta a respaldar.
        reason: Motivo del respaldo.
        dry_run: Si es ``True``, no escribe nada.

    Returns:
        El :class:`BackupRecord`, o ``None`` si está deshabilitado/dry-run.
    """
    return BackupManager().create_backup(source, reason=reason, dry_run=dry_run)


__all__ = ["BackupManager", "BackupRecord", "auto_backup"]
