from cryptography.fernet import Fernet, InvalidToken

from ..config import settings

_KEY_PATH = settings.data_dir / "secret.key"


def _get_key() -> bytes:
    if not _KEY_PATH.exists():
        _KEY_PATH.write_bytes(Fernet.generate_key())
    return _KEY_PATH.read_bytes()


_fernet = Fernet(_get_key())


def encrypt_text(value: str) -> str:
    if not value:
        return value
    return _fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str) -> str:
    if not value:
        return value
    if not value.startswith("gAAAA"):
        return value
    try:
        return _fernet.decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("敏感数据解密失败，密钥可能已变更") from exc
