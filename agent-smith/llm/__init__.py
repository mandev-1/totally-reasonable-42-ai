"""Centralized LLM provider config. Switch providers via LLM_PROVIDER env var."""

from llm.provider import get_client, get_provider_config

__all__ = ["get_client", "get_provider_config"]
