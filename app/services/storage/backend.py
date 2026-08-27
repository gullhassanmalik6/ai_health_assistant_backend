"""Future object-storage seam for reports, prescriptions, and medical images.

    FastAPI -> StorageBackend -> Firebase Storage / S3-compatible storage

Phase 1 does not upload medical files. Later phases should depend on this
interface rather than a single vendor SDK.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    async def upload(
        self,
        *,
        key: str,
        data: bytes | BinaryIO,
        content_type: str,
    ) -> str:
        """Store an object and return a durable key or URI."""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, *, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def generate_url(self, *, key: str, expires_in: int = 300) -> str:
        raise NotImplementedError
