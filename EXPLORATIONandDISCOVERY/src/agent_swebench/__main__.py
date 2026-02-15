"""SWE-bench Agent CLI (Section 4.4)."""

import argparse
import json
import sys
import time
from pathlib import Path

from agent_smith.agent.loop import TCOLoopConfig, run_tco_loop
from agent_smith.models.sandbox import SandboxConfig
from agent_smith.models.solution import SolutionOutput, StepMetrics
from agent_smith.models.task import SWEBenchTaskInput
from agent_smith.sandbox.runner import execute, get_tool_globals


# SWE-bench limits (Section 5.1.2)
SWEBENCH_MAX_ITER = 30
SWEBENCH_MAX_INPUT = 300_000
SWEBENCH_MAX_OUTPUT = 10_000
SWEBENCH_TIMEOUT = 900


def _load_system_prompt() -> str:
    path = Path(__file__).parent.parent / "agent_smith" / "prompts" / "system.txt"
    return path.read_text()


def main() -> None:
    parser = argparse.ArgumentParser(description="SWE-bench Agent")
    parser.add_argument("--task-file", required=True, help="Path to swebench_task.json")
    parser.add_argument("--output", required=True, help="Path to swebench_solution.json")
    parser.add_argument("--workdir", default=".", help="Working directory (Docker repo)")
    parser.add_argument(
        "--model",
        default="mock",
        help="LLM model",
    )
    parser.add_argument("--api-url", default="")
    parser.add_argument("--api-tokens", default="")
    args = parser.parse_args()

    task_path = Path(args.task_file)
    output_path = Path(args.output)
    workdir = Path(args.workdir)

    if not task_path.exists():
        print(f"Task file not found: {task_path}", file=sys.stderr)
        sys.exit(1)

    task_data = json.loads(task_path.read_text())
    task = SWEBenchTaskInput.model_validate(task_data)

    task_prompt = f"""SWE-bench task: {task.instance_id}

Problem statement:
{task.problem_statement}

Hints: {task.hints_text}

Docker image: {task.docker_image}
Eval script: {task.eval_script}

Use read_file, edit_file, search_code, run_tests, get_patch. Call final_answer with your git diff patch when done.
"""

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
            task_id=task.instance_id,
            benchmark="swebench",
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
    sandbox_config = get_tool_globals(config, workdir, task.eval_script)

    total_input = 0
    total_output = 0
    total_requests = 0

    def get_llm_response(prompt: str, _sys: str) -> tuple[str, int, int, float]:
        nonlocal total_input, total_output, total_requests
        content, stats = provider.complete(
            prompt, system=system_prompt, max_tokens=SWEBENCH_MAX_OUTPUT
        )
        total_input += stats.input_tokens
        total_output += stats.output_tokens
        total_requests += 1
        if total_input > SWEBENCH_MAX_INPUT or total_output > SWEBENCH_MAX_OUTPUT:
            raise RuntimeError("Token limit exceeded")
        return content, stats.input_tokens, stats.output_tokens, stats.request_time_ms

    def execute_code(code: str) -> tuple[str, str | None]:
        out, ans = execute(
            code, config, tool_globals=sandbox_config, base_dir=workdir, eval_script=task.eval_script
        )
        return out, ans

    def build_prompt(initial: str, obs: str) -> str:
        return f"{initial}\n\n--- Previous observation ---\n{obs}"

    tco_config = TCOLoopConfig(
        max_iterations=SWEBENCH_MAX_ITER,
        max_input_tokens=SWEBENCH_MAX_INPUT,
        max_output_tokens=SWEBENCH_MAX_OUTPUT,
        timeout_seconds=SWEBENCH_TIMEOUT,
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
            task_id=task.instance_id,
            benchmark="swebench",
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
                    timestamp="",
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
            timestamp="",
        )
        for s in states
    ]

    solution = SolutionOutput(
        task_id=task.instance_id,
        benchmark="swebench",
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
