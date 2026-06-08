"""Pruebas de seguridad y restauracion para respaldos/PBIX."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from powerbi_mcp.config import reload_settings
from powerbi_mcp.core.backup import BackupManager
from powerbi_mcp.core.exceptions import BackupError, PBIXError
from powerbi_mcp.pbip.pbix import extract_pbix
from powerbi_mcp.security.encryption import generate_key


def _configure_backup(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PBIMCP_BACKUP_DIR", str(tmp_path / "backups"))
    monkeypatch.setenv("PBIMCP_LOG_DIR", str(tmp_path / "logs"))
    reload_settings()


def test_restore_file_backup_overwrites_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure_backup(monkeypatch, tmp_path)
    source = tmp_path / "model.bim"
    source.write_text("version 1", encoding="utf-8")

    record = BackupManager().create_backup(source, reason="test")
    assert record is not None

    source.write_text("version 2", encoding="utf-8")
    restored = BackupManager().restore_backup(record.backup_id)

    assert restored == source.resolve()
    assert source.read_text(encoding="utf-8") == "version 1"


def test_encrypted_backup_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_backup(monkeypatch, tmp_path)
    monkeypatch.setenv("PBIMCP_BACKUP_ENCRYPT", "true")
    monkeypatch.setenv("PBIMCP_SECRET_KEY", generate_key())
    reload_settings()

    source = tmp_path / "secret.txt"
    source.write_text("sensible", encoding="utf-8")

    record = BackupManager().create_backup(source, reason="encrypted")
    assert record is not None
    assert record.encrypted is True
    assert record.backup_path.endswith(".zip.enc")
    assert not Path(record.backup_path.removesuffix(".enc")).exists()

    source.write_text("changed", encoding="utf-8")
    BackupManager().restore_backup(record.backup_id)

    assert source.read_text(encoding="utf-8") == "sensible"


def test_restore_rejects_zip_traversal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_backup(monkeypatch, tmp_path)
    source = tmp_path / "project"
    source.mkdir()
    (source / "safe.txt").write_text("safe", encoding="utf-8")

    record = BackupManager().create_backup(source, reason="test")
    assert record is not None
    backup_path = Path(record.backup_path)
    with zipfile.ZipFile(backup_path, "w") as zf:
        zf.writestr("../evil.txt", "owned")

    with pytest.raises(BackupError):
        BackupManager().restore_backup(record.backup_id)

    assert not (tmp_path / "evil.txt").exists()


def test_extract_pbix_rejects_zip_traversal(tmp_path: Path) -> None:
    pbix = tmp_path / "bad.pbix"
    with zipfile.ZipFile(pbix, "w") as zf:
        zf.writestr("../evil.txt", "owned")
        zf.writestr("Report/Layout", json.dumps({}))

    with pytest.raises(PBIXError):
        extract_pbix(pbix, tmp_path / "out")

    assert not (tmp_path / "evil.txt").exists()
