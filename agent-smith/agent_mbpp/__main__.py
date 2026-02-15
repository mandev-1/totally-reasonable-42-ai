#!/usr/bin/env python3
"""MBPP agent: reads task, generates code via LLM, runs tests via MCP, observes, retries."""
import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from openai import OpenAI

from agent_mbpp.pydantic_models import MBPPTaskInput, SolutionOutput, StepMetrics

DEFAULT_MCP_URL = "http://localhost:8765"

# MBPP hard limits
MAX_ITERATIONS = 10
MAX_INPUT_TOKENS = 4_000
MAX_OUTPUT_TOKENS = 1_000
MAX_TIME_SECONDS = 60


def call_mcp_run_tests(url: str, code: str, test_imports: list, test_list: list, timeout: float = 30.0) -> dict:
    """Call run_tests tool on MCP server. Returns {success, output, message}."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "run_tests",
            "arguments": {
                "code": code,
                "test_imports": test_imports,
                "test_list": test_list,
                "timeout": timeout,
            },
        },
    }
    data = json.dumps(req).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as resp:
            out = json.loads(resp.read().decode())
    except Exception as e:
        return {"success": False, "output": str(e), "message": f"MCP call failed: {e}"}

    if "error" in out:
        return {"success": False, "output": out["error"].get("message", ""), "message": "MCP error"}

    content = out.get("result", {}).get("content", [])
    if not content:
        return {"success": False, "output": "", "message": "Empty response"}
    text = content[0].get("text", "{}")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"success": False, "output": text, "message": "Invalid JSON response"}


def extract_code(text: str) -> str:
    """Extract Python code from LLM response (handles markdown code blocks)."""
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def main():
    parser = argparse.ArgumentParser(description="MBPP code generation agent")
    parser.add_argument("--task-file", type=Path, required=True, help="Path to task JSON")
    parser.add_argument("--output", type=Path, required=True, help="Path to write solution JSON")
    parser.add_argument("--mcp-server", default=os.environ.get("MCP_SERVER_URL", DEFAULT_MCP_URL), help="MCP server URL")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS, help=f"Max generation attempts (hard limit: {MAX_ITERATIONS})")
    parser.add_argument("--model", default="moonshotai/Kimi-K2-Instruct-0905", help="Model name")
    parser.add_argument("--api-url", default=os.environ.get("OPENAI_BASE_URL", "https://router.huggingface.co/v1"))
    parser.add_argument("--api-tokens", default=os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", "")))
    args = parser.parse_args()

    with open(args.task_file) as f:
        task = MBPPTaskInput.model_validate(json.load(f))

    task_id = task.task_id
    task_definition = task.task_definition
    function_definition = task.function_definition
    test_imports = task.test_imports
    test_list = task.test_list

    print("\n" + "=" * 60)
    print("TASK")
    print("=" * 60)
    print(f"Task ID: {task_id}")
    print(f"\nTask: {task_definition}")
    print(f"\nFunction:\n{function_definition}")
    if test_imports:
        print(f"\nTest imports:\n" + "\n".join(test_imports))
    if test_list:
        print(f"\nTests:\n" + "\n".join(test_list))
    print("=" * 60 + "\n")

    base_prompt = f"""Complete this Python function. Return only the function implementation, no explanation.

Task: {task_definition}

{function_definition}

Important: Handle edge cases gracefully. Consider empty input, zeros, negative numbers, single element. Avoid assumptions not stated in the task.

Public tests (your solution must pass these):
"""
    if test_imports:
        base_prompt += "\n".join(test_imports) + "\n"
    if test_list:
        base_prompt += "\n".join(test_list)

    start = datetime.now()
    client = OpenAI(base_url=args.api_url, api_key=args.api_tokens)
    steps: list[StepMetrics] = []
    total_input = 0
    total_output = 0
    solution = ""
    success = False

    messages = [{"role": "user", "content": base_prompt}]

    max_iters = min(args.max_iterations, MAX_ITERATIONS)
    for iteration in range(1, max_iters + 1):
        # Check total time limit
        if (datetime.now() - start).total_seconds() >= MAX_TIME_SECONDS:
            print(f"\nTimeout: exceeded {MAX_TIME_SECONDS}s limit")
            break

        # Check token limits before calling LLM
        if total_input >= MAX_INPUT_TOKENS:
            print(f"\nLimit: exceeded {MAX_INPUT_TOKENS} input tokens")
            break
        if total_output >= MAX_OUTPUT_TOKENS:
            print(f"\nLimit: exceeded {MAX_OUTPUT_TOKENS} output tokens")
            break

        print(f"\n--- Iteration {iteration} ---")
        try:
            completion = client.chat.completions.create(model=args.model, messages=messages)
        except Exception as e:
            print(f"LLM Error: {e}", file=sys.stderr)
            result = SolutionOutput(
                task_id=str(task_id),
                benchmark="mbpp",
                success=False,
                solution="",
                iterations=iteration,
                total_requests=iteration,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                total_time_seconds=round((datetime.now() - start).total_seconds(), 2),
                steps=steps,
                error=str(e),
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.model_dump_json(indent=2))
            sys.exit(1)

        usage = completion.usage or type("Usage", (), {"prompt_tokens": 0, "completion_tokens": 0})()
        total_input += getattr(usage, "prompt_tokens", 0) or 0
        total_output += getattr(usage, "completion_tokens", 0) or 0

        # Enforce token limits (stop if exceeded)
        if total_input > MAX_INPUT_TOKENS or total_output > MAX_OUTPUT_TOKENS:
            print(f"\nLimit: tokens exceeded (input={total_input}, output={total_output})")
            break

        solution = extract_code(completion.choices[0].message.content)

        print("\nSOLUTION:")
        print(solution or "(empty)")

        if not solution:
            messages.append({"role": "assistant", "content": completion.choices[0].message.content})
            messages.append({"role": "user", "content": "You must return valid Python code. Try again with only the function implementation."})
            steps.append(StepMetrics(step=iteration, input_tokens=getattr(usage, "prompt_tokens", 0) or 0, output_tokens=getattr(usage, "completion_tokens", 0) or 0, request_time_ms=0, timestamp=datetime.now().isoformat()))
            continue

        # Run tests via MCP (per-execution timeout capped by remaining total time)
        remaining_time = max(5, MAX_TIME_SECONDS - (datetime.now() - start).total_seconds())
        mcp_result = call_mcp_run_tests(args.mcp_server, solution, test_imports, test_list, timeout=min(30, remaining_time))
        success = mcp_result.get("success", False)
        output = mcp_result.get("output", "")

        steps.append(StepMetrics(step=iteration, input_tokens=getattr(usage, "prompt_tokens", 0) or 0, output_tokens=getattr(usage, "completion_tokens", 0) or 0, request_time_ms=round((datetime.now() - start).total_seconds() * 1000, 1), timestamp=datetime.now().isoformat()))

        print(f"\nTests: {'PASSED' if success else 'FAILED'}")
        if output:
            print(f"Output: {output[:500]}{'...' if len(output) > 500 else ''}")

        if success:
            break

        messages.append({"role": "assistant", "content": completion.choices[0].message.content})
        messages.append({"role": "user", "content": f"The tests failed. Output:\n{output}\n\nFix the code and try again. Return only the corrected function implementation."})

    elapsed = (datetime.now() - start).total_seconds()
    result = SolutionOutput(
        task_id=str(task_id),
        benchmark="mbpp",
        success=success,
        solution=solution,
        iterations=len(steps),
        total_requests=len(steps),
        total_input_tokens=total_input,
        total_output_tokens=total_output,
        total_time_seconds=round(elapsed, 2),
        steps=steps,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.model_dump_json(indent=2))

    print("\n" + "=" * 60)
    print(f"Wrote {args.output}")
    print(f"Success: {success}")
    print("=" * 60)


if __name__ == "__main__":
    main()
