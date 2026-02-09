"""Shared FastAPI dependencies."""

from __future__ import annotations

from functools import lru_cache

from app.config import Settings
from app.ml.llm import LLMClient
from app.providers.base import AccountingProvider
from app.providers.factory import get_provider


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_accounting_provider() -> AccountingProvider:
    return get_provider(get_settings())


def get_llm_client() -> LLMClient:
    return LLMClient(get_settings())
