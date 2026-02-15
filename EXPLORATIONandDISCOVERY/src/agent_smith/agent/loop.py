"""Thought → Code → Observation loop (Section 4.1)."""

from dataclasses import dataclass
from typing import Callable, Optional

from agent_smith.models.solution import StepMetrics


@dataclass
class AgentState:
    """State for one agent iteration."""

    step: int
    thought: str
    code: str
    observation: str
    input_tokens: int
    output_tokens: int
    request_time_ms: float


@dataclass
class TCOLoopConfig:
    """Configuration for the TCO loop."""

    max_iterations: int = 10
    max_input_tokens: int = 4_000
    max_output_tokens: int = 1_000
    timeout_seconds: int = 60


def extract_code_from_response(response: str) -> Optional[str]:
    """Extract LLM-generated Python code from model response."""
    markers = ["```python", "```"]
    for marker in markers:
        if marker in response:
            parts = response.split(marker)
            if len(parts) >= 2:
                code = parts[1].split("```")[0].strip()
                if code:
                    return code
    return None


def run_tco_loop(
    *,
    get_llm_response: Callable[[str, str], tuple[str, int, int, float]],
    execute_code: Callable[[str], tuple[str, Optional[str]]],
    build_prompt: Callable[[str, str], str],
    initial_task: str,
    config: TCOLoopConfig,
) -> tuple[str, list[AgentState]]:
    """Run Thought → Code → Observation loop until final_answer or limit."""
    history: list[AgentState] = []
    observation = (
        f"Task: {initial_task}\n\n"
        "You have access to tools. Generate Python code to solve the task."
    )
    final_answer: Optional[str] = None

    for step in range(1, config.max_iterations + 1):
        prompt = build_prompt(initial_task, observation)
        response, input_tokens, output_tokens, request_time_ms = get_llm_response(
            prompt, ""
        )

        code = extract_code_from_response(response)
        if not code:
            observation = (
                "No valid code block found. "
                "Please output Python code in a ```python block."
            )
        else:
            observation, final_answer = execute_code(code)

        history.append(
            AgentState(
                step=step,
                thought=(
                    response.split("```")[0].strip()
                    if "```" in response
                    else response[:500]
                ),
                code=code or "",
                observation=observation,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                request_time_ms=request_time_ms,
            )
        )

        if final_answer is not None:
            break

    return final_answer or observation, history
