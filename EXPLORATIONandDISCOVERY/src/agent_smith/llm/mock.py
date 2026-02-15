"""Mock LLM for testing without API keys."""

from agent_smith.llm.provider import LLMProvider, UsageStats


class MockLLMProvider(LLMProvider):
    """Returns canned responses for testing."""

    def __init__(self):
        self._tokens = ["mock-token"]

    def get_available_tokens(self):
        return self._tokens

    def complete(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 1024,
    ) -> tuple[str, UsageStats]:
        # Return a minimal response that extracts code
        return (
            """**Thought:** I will implement a simple solution.

**Code:**
```python
final_answer("mock solution")
```""",
            UsageStats(input_tokens=100, output_tokens=50, request_time_ms=10.0),
        )
