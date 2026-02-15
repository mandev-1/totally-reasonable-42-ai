"""LLM provider abstraction — multiple providers, token tracking, rotation (Section 4.6)."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class UsageStats:
    """Token and cost tracking per request."""

    input_tokens: int
    output_tokens: int
    request_time_ms: float


class LLMProvider(ABC):
    """Abstract LLM provider."""

    @abstractmethod
    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> tuple[str, UsageStats]:
        """Return (response_text, usage_stats)."""
        ...

    @abstractmethod
    def get_available_tokens(self) -> List[str]:
        """Return list of API tokens for rotation."""
        ...


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible API (OpenRouter, Together, Groq, etc.)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        tokens: List[str],
        api_key_header: str = "Authorization",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._tokens = list(tokens) if tokens else []
        self._token_idx = 0
        self.api_key_header = api_key_header

    def get_available_tokens(self) -> List[str]:
        return list(self._tokens)

    def _next_token(self) -> Optional[str]:
        if not self._tokens:
            return None
        tok = self._tokens[self._token_idx % len(self._tokens)]
        self._token_idx += 1
        return tok

    def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 1024,
    ) -> tuple[str, UsageStats]:
        import httpx

        api_key = self._next_token()
        if not api_key:
            raise ValueError("No API token configured")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=60.0) as client:
                r = client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                    },
                    headers={self.api_key_header: f"Bearer {api_key}"},
                )
                r.raise_for_status()
                data = r.json()
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000
            raise RuntimeError(f"LLM request failed: {e}") from e

        elapsed_ms = (time.perf_counter() - start) * 1000
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        stats = UsageStats(
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            request_time_ms=elapsed_ms,
        )
        return content, stats
