"""Private local disk storage for profile photos. Not a public bucket."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import BinaryIO
from urllib.parse import quote

from app.core.config import settings
from app.core.constants import PHOTO_SIGNED_URL_TTL_SECONDS
from app.core.security import utcnow
from app.services.storage.backend import StorageBackend


class LocalPrivateStorage(StorageBackend):
    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.STORAGE_DIR).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if not str(target).startswith(str(self.root)):
            raise ValueError("Invalid storage key")
        target.parent.mkdir(parents=True, exist_ok=True)
        return target

    async def upload(self, *, key: str, data: bytes | BinaryIO, content_type: str) -> str:
        payload = data.read() if hasattr(data, "read") else data
        path = self._path(key)
        path.write_bytes(payload)
        return key

    async def delete(self, *, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    async def generate_url(self, *, key: str, expires_in: int | None = None) -> str:
        ttl = expires_in if expires_in is not None else PHOTO_SIGNED_URL_TTL_SECONDS
        exp = int(utcnow().timestamp()) + ttl
        signature = sign_photo_key(key, exp)
        base = settings.PUBLIC_API_BASE_URL.rstrip("/")
        return f"{base}/api/v1/profile/photo/file?key={quote(key)}&exp={exp}&sig={signature}"

    async def read(self, *, key: str) -> bytes | None:
        path = self._path(key)
        if not path.exists():
            return None
        return path.read_bytes()


def sign_photo_key(key: str, exp: int) -> str:
    payload = f"{key}:{exp}".encode("utf-8")
    return hmac.new(settings.APP_SECRET_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def verify_photo_signature(key: str, exp: int, signature: str) -> bool:
    if exp < int(utcnow().timestamp()):
        return False
    expected = sign_photo_key(key, exp)
    return hmac.compare_digest(expected, signature)


_storage: LocalPrivateStorage | None = None


def get_storage() -> LocalPrivateStorage:
    global _storage
    if _storage is None:
        _storage = LocalPrivateStorage()
    return _storage
