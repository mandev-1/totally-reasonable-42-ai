"""Centralized LLM provider config. Toggle providers via LLM_PROVIDER env var.

Usage:
    export LLM_PROVIDER=google    # Use Google AI Studio (genai SDK)
    export LLM_PROVIDER=huggingface  # Use Hugging Face Inference
    export LLM_PROVIDER=openai   # Use OpenAI API
    export LLM_PROVIDER=groq    # Use Groq
    export LLM_PROVIDER=qwen    # Use Hugging Face Qwen 2.5 0.5B
    export LLM_PROVIDER=ollama  # Use Ollama (local Qwen, etc.)

Or override per-run:
    uv run python -m agent_mbpp ... --provider google
"""
import json
import os
from typing import Any, NamedTuple

from openai import OpenAI


class ProviderConfig(NamedTuple):
    """LLM provider configuration."""

    base_url: str
    api_key: str
    default_model: str
    name: str


# Provider presets. Add new providers here.
PROVIDERS = {
    "huggingface": ProviderConfig(
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", "")),
        default_model="moonshotai/Kimi-K2-Instruct-0905",
        name="Hugging Face",
    ),
    "google": ProviderConfig(
        base_url="",  # Not used for genai SDK
        api_key=os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", "")),
        default_model="gemini-2.5-flash-lite",
        name="Google AI Studio (genai)",
    ),
    "openai": ProviderConfig(
        base_url="https://api.openai.com/v1",
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        default_model="gpt-4o-mini",
        name="OpenAI",
    ),
    "groq": ProviderConfig(
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY", ""),
        default_model="openai/gpt-oss-20b",
        name="Groq",
    ),
    "qwen": ProviderConfig(
        base_url="https://router.huggingface.co/v1",
        api_key=os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", "")),
        default_model="Qwen/Qwen2.5-0.5B-Instruct",
        name="Hugging Face (Qwen 2.5 0.5B)",
    ),
    "ollama": ProviderConfig(
        base_url="http://localhost:11434/v1",
        api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),  # unused, but required by client
        default_model="qwen2.5:0.5b",
        name="Ollama (local)",
    ),
}


def get_provider_config(
    provider: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> ProviderConfig:
    """Get provider config. Provider can be overridden by env LLM_PROVIDER."""
    provider = provider or os.environ.get("LLM_PROVIDER", "google")
    provider = provider.lower()

    if provider not in PROVIDERS:
        raise ValueError(
            f"Unknown provider: {provider}. Choose from: {list(PROVIDERS.keys())}"
        )

    cfg = PROVIDERS[provider]
    return ProviderConfig(
        base_url=base_url or cfg.base_url,
        api_key=api_key or cfg.api_key,
        default_model=model or cfg.default_model,
        name=cfg.name,
    )


class _GenAICompletionAdapter:
    """Mimics OpenAI completion response for genai responses."""

    def __init__(self, response: Any, model: str):
        self._response = response
        self.model = model
        self.choices = [_GenAIChoiceAdapter(response)]
        self.usage = _GenAIUsageAdapter(response)


class _GenAIChoiceAdapter:
    def __init__(self, response: Any):
        self.message = _GenAIMessageAdapter(response)


class _GenAIMessageAdapter:
    def __init__(self, response: Any):
        text = ""
        tool_calls = []
        candidates = getattr(response, "candidates", None) or []
        if candidates:
            c = candidates[0]
            content = getattr(c, "content", None)
            parts = getattr(content, "parts", []) if content else []
            for part in parts:
                pt = getattr(part, "text", None)
                if pt:
                    text += pt
                fc = getattr(part, "function_call", None)
                if fc:
                    name = getattr(fc, "name", "") or ""
                    args = getattr(fc, "args", None) or {}
                    tool_calls.append(
                        type(
                            "ToolCall",
                            (),
                            {
                                "id": f"call_{name}",
                                "function": type(
                                    "Fn",
                                    (),
                                    {
                                        "name": name,
                                        "arguments": json.dumps(dict(args)),
                                    },
                                )(),
                            },
                        )()
                    )
        self.content = text or None
        self.tool_calls = tool_calls if tool_calls else None


class _GenAIUsageAdapter:
    def __init__(self, response: Any):
        usage = getattr(response, "usage_metadata", None)
        self.prompt_tokens = getattr(usage, "prompt_token_count", None) or 0
        self.completion_tokens = getattr(usage, "candidates_token_count", None) or 0


def _messages_to_genai_contents(messages: list[dict]) -> list[Any]:
    """Convert OpenAI-style messages to genai Content format."""
    from google.genai import types

    contents = []
    pending_tool_names: list[str] = []

    for m in messages:
        role = m.get("role", "user")
        if role == "system":
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"[System]: {m.get('content', '')}")],
                )
            )
            continue
        if role == "user":
            content = m.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                )
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content or "")],
                )
            )
        elif role == "assistant":
            parts = []
            if m.get("content"):
                parts.append(types.Part.from_text(text=m["content"]))
            pending_tool_names = []
            for tc in m.get("tool_calls") or []:
                fn = tc.get("function", {})
                args = {}
                try:
                    args = json.loads(fn.get("arguments", "{}") or "{}")
                except json.JSONDecodeError:
                    pass
                parts.append(
                    types.Part.from_function_call(
                        name=fn.get("name", ""),
                        args=args,
                    )
                )
                pending_tool_names.append(fn.get("name", ""))
            if parts:
                contents.append(types.Content(role="model", parts=parts))
        elif role == "tool":
            # Pair with previous assistant's tool calls by order
            name = pending_tool_names.pop(0) if pending_tool_names else "result"
            contents.append(
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_function_response(
                            name=name,
                            response={"result": m.get("content", "")},
                        )
                    ],
                )
            )
    return contents


def _openai_tools_to_genai(tools: list[dict]) -> list[Any]:
    """Convert OpenAI tool definitions to genai FunctionDeclaration."""
    from google.genai import types

    result = []
    for t in tools:
        fn = t.get("function", {})
        params = fn.get("parameters", {})
        props = params.get("properties", {}) or {}
        req = params.get("required", []) or []
        result.append(
            types.FunctionDeclaration(
                name=fn.get("name", ""),
                description=fn.get("description", ""),
                parameters=types.Schema(
                    type="OBJECT",
                    properties={
                        k: types.Schema(
                            type="STRING",
                            description=v.get("description", ""),
                        )
                        for k, v in props.items()
                    },
                    required=req,
                ),
            )
        )
    return result


class GenAIClientAdapter:
    """Adapter that provides OpenAI-style chat.completions.create() using google.genai."""

    def __init__(self, api_key: str | None = None):
        from google import genai

        self._client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    @property
    def chat(self):
        return self

    @property
    def completions(self):
        return self

    def create(
        self,
        model: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        tool_choice: str | None = None,
        **kwargs,
    ):
        from google.genai import types

        contents = _messages_to_genai_contents(messages)
        config = types.GenerateContentConfig()
        if tools:
            config.tools = [
                types.Tool(function_declarations=_openai_tools_to_genai(tools))
            ]

        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
        return _GenAICompletionAdapter(response, model)


def get_client(
    provider: str | None = None,
    *,
    base_url: str | None = None,
    api_key: str | None = None,
) -> OpenAI | GenAIClientAdapter:
    """Get LLM client for the configured provider."""
    provider = provider or os.environ.get("LLM_PROVIDER", "google")
    provider = provider.lower()

    if provider == "google":
        cfg = get_provider_config(provider=provider, api_key=api_key)
        return GenAIClientAdapter(api_key=api_key or cfg.api_key)

    cfg = get_provider_config(
        provider=provider, base_url=base_url, api_key=api_key
    )
    return OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
