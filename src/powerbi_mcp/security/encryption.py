"""Encriptación simétrica para secretos y respaldos sensibles.

Usa **Fernet** (de la librería ``cryptography``), que implementa AES-128 en modo
CBC con HMAC-SHA256 para autenticación (AEAD), rotación de claves y marca de
tiempo. Es el estándar recomendado para cifrado simétrico de alto nivel en
Python.

La clave maestra se obtiene de la configuración (``settings.secret_key``); puede
generarse una nueva con :func:`generate_key`. También se puede derivar una clave
a partir de una contraseña con :func:`derive_key_from_password` (PBKDF2).

Ejecutable como módulo para generar una clave::

    python -m powerbi_mcp.security.encryption --generate-key
"""

from __future__ import annotations

import base64
from pathlib import Path

from powerbi_mcp.config import get_settings
from powerbi_mcp.core.exceptions import SecurityError
from powerbi_mcp.core.logger import get_logger

logger = get_logger(__name__)


def generate_key() -> str:
    """Genera una nueva clave Fernet aleatoria.

    Returns:
        La clave en formato urlsafe-base64 (apta para ``PBIMCP_SECRET_KEY``).

    Raises:
        SecurityError: Si ``cryptography`` no está instalado.
    """
    try:
        from cryptography.fernet import Fernet
    except ImportError as exc:  # pragma: no cover
        raise SecurityError("La librería 'cryptography' no está instalada.") from exc
    return Fernet.generate_key().decode("utf-8")


def derive_key_from_password(password: str, *, salt: bytes | None = None) -> tuple[str, str]:
    """Deriva una clave Fernet a partir de una contraseña usando PBKDF2.

    Args:
        password: Contraseña de la que derivar la clave.
        salt: Salt en bytes. Si es ``None``, se genera uno aleatorio.

    Returns:
        Tupla ``(clave_base64, salt_base64)``. Guarda el salt para poder
        re-derivar la misma clave.

    Raises:
        SecurityError: Si ``cryptography`` no está instalado.
    """
    try:
        import os

        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    except ImportError as exc:  # pragma: no cover
        raise SecurityError("La librería 'cryptography' no está instalada.") from exc

    salt = salt or os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=480_000)
    key = base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))
    return key.decode("utf-8"), base64.urlsafe_b64encode(salt).decode("utf-8")


class Encryptor:
    """Encripta y desencripta datos con una clave Fernet.

    Args:
        key: Clave Fernet. Si es ``None``, se toma de ``settings.secret_key``.

    Raises:
        SecurityError: Si no hay clave disponible o es inválida.
    """

    def __init__(self, key: str | None = None) -> None:
        resolved = key or get_settings().secret_key
        if not resolved:
            raise SecurityError(
                "No hay clave de encriptación. Define PBIMCP_SECRET_KEY o pásala "
                "explícitamente (genera una con generate_key())."
            )
        try:
            from cryptography.fernet import Fernet

            self._fernet = Fernet(resolved.encode("utf-8") if isinstance(resolved, str) else resolved)
        except ImportError as exc:  # pragma: no cover
            raise SecurityError("La librería 'cryptography' no está instalada.") from exc
        except (ValueError, TypeError) as exc:
            raise SecurityError("Clave de encriptación inválida.") from exc

    def encrypt(self, plaintext: str) -> str:
        """Encripta una cadena de texto.

        Args:
            plaintext: Texto plano a encriptar.

        Returns:
            El texto cifrado (token Fernet en base64).
        """
        token = self._fernet.encrypt(plaintext.encode("utf-8"))
        return token.decode("utf-8")

    def decrypt(self, token: str) -> str:
        """Desencripta un token Fernet.

        Args:
            token: Texto cifrado producido por :meth:`encrypt`.

        Returns:
            El texto plano original.

        Raises:
            SecurityError: Si el token es inválido o la clave no corresponde.
        """
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except Exception as exc:
            raise SecurityError("No se pudo desencriptar (token o clave inválidos).") from exc

    def encrypt_file(self, source: str | Path, target: str | Path | None = None) -> Path:
        """Encripta el contenido de un archivo.

        Args:
            source: Archivo a encriptar.
            target: Archivo de salida. Por defecto, ``<source>.enc``.

        Returns:
            La ruta del archivo encriptado.

        Raises:
            SecurityError: Si falla la lectura/escritura.
        """
        src = Path(source).expanduser().resolve()
        dst = Path(target).expanduser().resolve() if target else src.with_suffix(src.suffix + ".enc")
        try:
            data = src.read_bytes()
            dst.write_bytes(self._fernet.encrypt(data))
        except OSError as exc:
            raise SecurityError("Fallo al encriptar el archivo.", details={"error": str(exc)}) from exc
        logger.info("Archivo encriptado: %s", dst.name)
        return dst

    def decrypt_file(self, source: str | Path, target: str | Path) -> Path:
        """Desencripta un archivo previamente encriptado.

        Args:
            source: Archivo encriptado.
            target: Archivo de salida con el contenido descifrado.

        Returns:
            La ruta del archivo descifrado.

        Raises:
            SecurityError: Si falla la operación.
        """
        src = Path(source).expanduser().resolve()
        dst = Path(target).expanduser().resolve()
        try:
            data = src.read_bytes()
            dst.write_bytes(self._fernet.decrypt(data))
        except OSError as exc:
            raise SecurityError("Fallo al leer/escribir el archivo.", details={"error": str(exc)}) from exc
        except Exception as exc:
            raise SecurityError("No se pudo desencriptar el archivo.") from exc
        return dst


def _cli() -> int:  # pragma: no cover - utilidad de línea de comandos
    """CLI mínima para generar claves."""
    import argparse

    parser = argparse.ArgumentParser(description="Utilidades de encriptación powerbi-mcp.")
    parser.add_argument("--generate-key", action="store_true", help="Genera una clave Fernet.")
    args = parser.parse_args()
    if args.generate_key:
        print(generate_key())
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_cli())


__all__ = [
    "Encryptor",
    "derive_key_from_password",
    "generate_key",
]
