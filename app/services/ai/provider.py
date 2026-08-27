"""Future AI provider seam. Do not put provider API keys in Flutter.

When Phase 3+ lands:

    Flutter/Web -> FastAPI -> AIService -> AIProvider (OpenAI | Gemini) -> FastAPI -> client

Phase 1 only defines the interface so later modules can be added without rewriting
auth, profile, or persistence layers.
"""

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    """Switchable model provider. Implementations belong in later phases."""

    provider_name: str

    @abstractmethod
    async def generate(self, *, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        raise NotImplementedError


class AIService:
    """Application-facing AI facade. Bind a provider at startup in a later phase."""

    def __init__(self, provider: AIProvider | None = None) -> None:
        self.provider = provider

    async def generate(self, *, messages: list[dict[str, Any]], **kwargs: Any) -> str:
        if self.provider is None:
            raise RuntimeError("No AI provider is configured.")
        return await self.provider.generate(messages=messages, **kwargs)
