"""MBPP Agent CLI (Section 4.3)."""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

from agent_smith.agent.loop import TCOLoopConfig, run_tco_loop
from agent_smith.models.sandbox import SandboxConfig
from agent_smith.models.solution import SolutionOutput, StepMetrics
from agent_smith.models.task import MBPPTaskInput
from agent_smith.sandbox.runner import execute, get_tool_globals


# MBPP limits (Section 5.1.1)
MBPP_MAX_ITER = 10
MBPP_MAX_INPUT = 4_000
MBPP_MAX_OUTPUT = 1_000
MBPP_TIMEOUT = 60


def _load_system_prompt() -> str:
    path = Path(__file__).parent.parent / "agent_smith" / "prompts" / "system.txt"
    return path.read_text()


def main() -> None:
    parser = argparse.ArgumentParser(description="MBPP Agent")
    parser.add_argument("--task-file", required=True, help="Path to mbpp_task.json")
    parser.add_argument("--output", required=True, help="Path to mbpp_solution.json")
    parser.add_argument(
        "--model",
        default="mock",
        help="LLM model (mock, or openai-compatible model name)",
    )
    parser.add_argument(
        "--api-url",
        default="",
        help="OpenAI-compatible API base URL",
    )
    parser.add_argument(
        "--api-tokens",
        default="",
        help="Comma-separated API tokens for rotation",
    )
    args = parser.parse_args()

    task_path = Path(args.task_file)
    output_path = Path(args.output)

    if not task_path.exists():
        print(f"Task file not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    task_data = json.loads(task_path.read_text())
    task = MBPPTaskInput.model_validate(task_data)

    # Build task prompt
    task_prompt = f"""Task ID: {task.task_id}

Task definition:
{task.task_definition}

Function to implement:
{task.function_definition}

Test imports: {task.test_imports}
Test list: {task.test_list}

Write Python code to implement the function and call final_answer with your solution code.
"""

    # Setup LLM
    try:
        if args.model == "mock" or not args.api_tokens:
            from agent_smith.llm.mock import MockLLMProvider

            provider = MockLLMProvider()
        else:
            from agent_smith.llm.provider import OpenAICompatibleProvider

            tokens = [t.strip() for t in args.api_tokens.split(",") if t.strip()]
            base_url = args.api_url or "https://openrouter.ai/api"
            provider = OpenAICompatibleProvider(base_url, args.model, tokens)
    except Exception as e:
        solution = SolutionOutput(
            task_id=str(task.task_id),
            benchmark="mbpp",
            success=False,
            solution="",
            iterations=0,
            total_requests=0,
            total_input_tokens=0,
            total_output_tokens=0,
            total_time_seconds=0.0,
            steps=[],
            error=str(e),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(solution.model_dump_json(indent=2))
        sys.exit(1)

    system_prompt = _load_system_prompt()
    config = SandboxConfig()
    sandbox_config = get_tool_globals(config, Path("."), "python -m pytest")

    total_input = 0
    total_output = 0
    total_requests = 0

    def get_llm_response(prompt: str, _sys: str) -> tuple[str, int, int, float]:
        nonlocal total_input, total_output, total_requests
        content, stats = provider.complete(
            prompt, system=system_prompt, max_tokens=MBPP_MAX_OUTPUT
        )
        total_input += stats.input_tokens
        total_output += stats.output_tokens
        total_requests += 1
        if total_input > MBPP_MAX_INPUT or total_output > MBPP_MAX_OUTPUT:
            raise RuntimeError("Token limit exceeded")
        return content, stats.input_tokens, stats.output_tokens, stats.request_time_ms

    def execute_code(code: str) -> tuple[str, str | None]:
        out, ans = execute(
            code, config, tool_globals=sandbox_config, base_dir=Path(".")
        )
        return out, ans

    def build_prompt(initial: str, obs: str) -> str:
        return f"{initial}\n\n--- Previous observation ---\n{obs}"

    tco_config = TCOLoopConfig(
        max_iterations=MBPP_MAX_ITER,
        max_input_tokens=MBPP_MAX_INPUT,
        max_output_tokens=MBPP_MAX_OUTPUT,
        timeout_seconds=MBPP_TIMEOUT,
    )

    start = time.perf_counter()
    states: list = []
    try:
        final_answer, states = run_tco_loop(
            get_llm_response=get_llm_response,
            execute_code=execute_code,
            build_prompt=build_prompt,
            initial_task=task_prompt,
            config=tco_config,
        )
    except Exception as e:
        elapsed = time.perf_counter() - start
        solution = SolutionOutput(
            task_id=str(task.task_id),
            benchmark="mbpp",
            success=False,
            solution="",
            iterations=len(states),
            total_requests=total_requests,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_time_seconds=elapsed,
            steps=[
                StepMetrics(
                    step=s.step,
                    input_tokens=s.input_tokens,
                    output_tokens=s.output_tokens,
                    request_time_ms=s.request_time_ms,
                    timestamp=datetime.now().isoformat(),
                )
                for s in states
            ],
            error=str(e),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(solution.model_dump_json(indent=2))
        sys.exit(1)

    elapsed = time.perf_counter() - start
    steps = [
        StepMetrics(
            step=s.step,
            input_tokens=s.input_tokens,
            output_tokens=s.output_tokens,
            request_time_ms=s.request_time_ms,
            timestamp=datetime.now().isoformat(),
        )
        for s in states
    ]

    solution = SolutionOutput(
        task_id=str(task.task_id),
        benchmark="mbpp",
        success=bool(final_answer),
        solution=final_answer or "",
        iterations=len(states),
        total_requests=total_requests,
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_time_seconds=elapsed,
        steps=steps,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(solution.model_dump_json(indent=2))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
