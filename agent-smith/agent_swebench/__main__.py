#!/usr/bin/env python3
"""SWE-bench agent: solves tasks inside Dockerized SWE-bench environment.

Flow:
1. Load task (docker_image, problem_statement, eval_script)
2. Pull and start SWE-bench Docker container
3. Run MCP server inside container (file ops, code search, run_tests, get_patch)
4. Agent loop: LLM + tool calls until patch is ready or max iterations
5. Output SolutionOutput with patch
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from llm.provider import get_client, get_provider_config
from MCP.execution import parse_eval_script
from tools.pydantic_models import SWEBenchTaskInput, SolutionOutput, StepMetrics

DEFAULT_MCP_PORT = 8766
MAX_ITERATIONS = 50
MAX_INPUT_TOKENS = 300_000
MAX_OUTPUT_TOKENS = 10_000
MAX_TIME_SECONDS = 900.0
EXPLORATION_TOOLS = {
    "get_repo_tree",
    "find_relevant",
    "search_symbol",
    "search_code",
    "list_files",
    "find_references",
    "read_file",
}
ACTION_TOOLS = {"edit_file", "run_tests", "get_patch", "validate_patch"}
ROOT_FILEPATH = "ROOT.md"


def call_mcp_tool(url: str, tool_name: str, arguments: dict, timeout: float = 60.0) -> dict:
    """Call MCP tool via JSON-RPC HTTP. Returns {success, text, error}."""
    req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }
    import urllib.request

    data = json.dumps(req).encode("utf-8")
    request = urllib.request.Request(url, data=data, method="POST")
    request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            out = json.loads(resp.read().decode())
    except Exception as e:
        return {"success": False, "text": "", "error": str(e)}

    if "error" in out:
        return {
            "success": False,
            "text": out["error"].get("message", ""),
            "error": out["error"].get("message", "MCP error"),
        }

    content = out.get("result", {}).get("content", [])
    if not content:
        return {"success": False, "text": "", "error": "Empty response"}
    text = content[0].get("text", "")
    return {"success": True, "text": text, "error": None}


def _compact_lines(text: str, head: int, tail: int) -> str:
    lines = text.splitlines()
    if len(lines) <= head + tail + 1:
        return text
    omitted = len(lines) - head - tail
    return "\n".join(lines[:head] + [f"... [{omitted} lines omitted] ..."] + lines[-tail:])


def _compact_tool_payload(name: str, text: str) -> str:
    """Reduce token usage sent to LLM while logs keep full output."""
    if name == "read_file":
        return _compact_lines(text, head=120, tail=30)
    if name in {"get_repo_tree", "find_relevant", "search_code", "list_files", "find_references"}:
        return _compact_lines(text, head=120, tail=20)
    if len(text) > 5000:
        return text[:5000] + "\n... [truncated for context efficiency]"
    return text


def _normalize_custom_eval_script(eval_script_value: str) -> str:
    cmd = (eval_script_value or "").strip()
    if not cmd:
        return cmd
    if "::" in cmd and not any(
        cmd.startswith(prefix)
        for prefix in ("pytest ", "python -m pytest ", "py.test ", "nosetests ")
    ):
        return f"python -m pytest {cmd} -q"
    if cmd.startswith("pytest "):
        return "python -m pytest " + cmd[len("pytest "):]
    return cmd


def _extract_failed_tests_from_summary(summary: str) -> list[str]:
    tests: list[str] = []
    for line in summary.splitlines():
        s = line.strip()
        if s.startswith("FAILED "):
            tests.append(s.replace("FAILED ", "", 1))
    return tests[:5]


def _extract_actionable_failure_output(output: str) -> str:
    """
    Keep failure-relevant test output; drop env/setup noise.
    Prefers lines between SWE-bench test markers, then filters to assertions/tracebacks.
    """
    if not output:
        return ""
    lines = output.splitlines()

    start_idx = 0
    end_idx = len(lines)
    for i, line in enumerate(lines):
        if ">>>>> Start Test Output" in line:
            start_idx = i + 1
            break
    for i in range(start_idx, len(lines)):
        if ">>>>> End Test Output" in lines[i]:
            end_idx = i
            break
    test_lines = lines[start_idx:end_idx]
    if not test_lines:
        test_lines = lines

    filtered: list[str] = []
    for ln in test_lines:
        s = ln.strip()
        if (
            s.startswith("FAILED ")
            or s.startswith("E   ")
            or "AssertionError" in s
            or s.startswith("Traceback")
            or s.startswith("ERROR ")
            or s.startswith("___")
            or "== FAILURES ==" in s
        ):
            filtered.append(ln)

    if filtered:
        return "\n".join(filtered[-160:])
    return "\n".join(test_lines[-120:])


# SWE-bench optimized. recommended_workflow: get_repo_tree -> find_relevant -> search_symbol -> read_file -> edit_file -> get_patch -> run_tests
SWEBENCH_TOOLS = [
    {"type": "function", "function": {"name": "get_repo_tree", "description": "FIRST STEP. Returns indented tree of the repository. Use to understand structure and locate likely source/test directories before reading files.", "parameters": {"type": "object", "properties": {"base_path": {"type": "string"}, "max_depth": {"type": "integer"}, "max_lines": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "find_relevant", "description": "PRIMARY SEARCH. Keywords from problem (e.g. session headers). Prefer over search_code for natural-language bugs.", "parameters": {"type": "object", "properties": {"keywords": {"type": "string"}}, "required": ["keywords"]}}},
    {"type": "function", "function": {"name": "search_symbol", "description": "Find def/class by name. Use after identifying a symbol to jump to implementation.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {"name": "search_code", "description": "Regex search. Use when you know exact pattern. Prefer find_relevant for vague queries.", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "list_files", "description": "List files in directory. Prefer get_repo_tree for initial exploration.", "parameters": {"type": "object", "properties": {"directory": {"type": "string"}, "pattern": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "find_references", "description": "Find usages of a symbol. Use to understand impact before editing.", "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "filepath": {"type": "string"}, "line": {"type": "integer"}}, "required": ["name", "filepath", "line"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read file. Use only after narrowing via tree/find_relevant/search. Prefer start_line/end_line for large files.", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["filepath"]}}},
    {"type": "function", "function": {"name": "edit_file", "description": "Replace exact string. old_str must match exactly. Read first. Use for minimal modifications.", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "old_str": {"type": "string"}, "new_str": {"type": "string"}}, "required": ["filepath", "old_str", "new_str"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Create file. Prefer edit_file for existing files.", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "content": {"type": "string"}}, "required": ["filepath", "content"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Delete a file if it exists. Used for temporary analysis artifacts.", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}}, "required": ["filepath"]}}},
    {"type": "function", "function": {"name": "validate_patch", "description": "Validate patch format before run_tests.", "parameters": {"type": "object", "properties": {"patch": {"type": "string"}}}}},
    {"type": "function", "function": {"name": "run_tests", "description": "Run tests. Returns failure_summary when failing. Avoid repeated runs without narrowing.", "parameters": {"type": "object", "properties": {"eval_script": {"type": "string"}, "timeout": {"type": "integer"}}, "required": ["eval_script"]}}},
    {"type": "function", "function": {"name": "run_root_cause_analysis", "description": "Analyze failed run_tests output and return root-cause summary with code citations.", "parameters": {"type": "object", "properties": {"failure_summary": {"type": "string"}, "output": {"type": "string"}, "last_edit_file": {"type": "string"}}, "required": ["failure_summary"]}}},
    {"type": "function", "function": {"name": "get_patch", "description": "Get unified diff of changes. Use to inspect modifications before finalizing.", "parameters": {"type": "object", "properties": {}}}},
]


def docker_pull(image: str) -> bool:
    """Pull Docker image. Returns True on success."""
    try:
        subprocess.run(
            ["docker", "pull", image],
            check=True,
            capture_output=True,
            timeout=600,
        )
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"Docker pull failed: {e}", file=sys.stderr)
        return False


def docker_run_container(image: str, port: int, mount_src: Path) -> str | None:
    """Start container, return container ID or None."""
    try:
        result = subprocess.run(
            [
                "docker", "run", "-d",
                "-p", f"{port}:{port}",
                "-v", f"{mount_src}:/agent",
                "-e", f"TESTBED_PATH=/testbed",
                "-e", f"PYTHONPATH=/agent",
                image,
                "tail", "-f", "/dev/null",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"Docker run failed: {result.stderr}", file=sys.stderr)
            return None
        return result.stdout.strip()
    except Exception as e:
        print(f"Docker run failed: {e}", file=sys.stderr)
        return None


def docker_stop(container_id: str) -> None:
    """Stop and remove container."""
    try:
        subprocess.run(["docker", "stop", container_id], capture_output=True, timeout=30)
        subprocess.run(["docker", "rm", container_id], capture_output=True, timeout=30)
    except Exception:
        pass


def start_mcp_in_container(container_id: str, port: int) -> bool:
    """Start MCP server inside container. Returns True if started."""
    cmd = [
        "docker", "exec", "-d", container_id,
        "bash", "-c",
        f"cd /agent && PYTHONPATH=/agent TESTBED_PATH=/testbed python -m MCP.swe_tools --port {port}",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if r.returncode != 0:
            print(f"MCP start stderr: {r.stderr}", file=sys.stderr)
        time.sleep(3)  # Allow server to start
        return True
    except Exception as e:
        print(f"Failed to start MCP in container: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(description="SWE-bench agent (Dockerized)")
    parser.add_argument("--task-file", type=Path, required=True, help="Path to task JSON")
    parser.add_argument("--output", type=Path, required=True, help="Path to write solution JSON")
    parser.add_argument("--log", type=Path, help="Path to write run log (default: <output_dir>/swebench_run.log)")
    parser.add_argument("--mcp-port", type=int, default=DEFAULT_MCP_PORT, help="MCP server port")
    parser.add_argument("--max-iterations", type=int, default=MAX_ITERATIONS)
    parser.add_argument("--provider", default=os.environ.get("LLM_PROVIDER", "huggingface"), help="LLM provider: huggingface, google, openai, ollama")
    parser.add_argument("--model", help="Model name (default from provider)")
    parser.add_argument("--api-url", help="Override API base URL")
    parser.add_argument("--api-tokens", help="Override API key")
    parser.add_argument("--llm-timeout", type=float, default=180, help="LLM request timeout in seconds (default 180; use 60 for fast fail)")
    parser.add_argument("--max-tokens", type=int, default=1024, help="Max tokens per LLM response (default 1024)")
    parser.add_argument("--no-docker", action="store_true", help="Skip Docker; use existing MCP server (e.g. for dev)")
    args = parser.parse_args()

    cfg = get_provider_config(
        provider=args.provider,
        base_url=args.api_url,
        api_key=args.api_tokens,
    )
    model = args.model or cfg.default_model

    if args.provider.lower() == "ollama":
        print("Note: Ollama on CPU is slow (minutes per request). Use --provider google or groq for faster runs.\n")

    if args.provider.lower() == "huggingface" and not (args.api_tokens or cfg.api_key):
        print("Error: Hugging Face requires HF_TOKEN (or --api-tokens). Get one at https://huggingface.co/settings/tokens")
        print("Or use --provider ollama for local, or --provider google with GEMINI_API_KEY\n")
        sys.exit(1)

    with open(args.task_file) as f:
        task = SWEBenchTaskInput.model_validate(json.load(f))

    instance_id = task.instance_id
    docker_image = task.docker_image
    problem_statement = task.problem_statement
    hints_text = task.hints_text or ""
    eval_script = task.eval_script

    # Parse eval_script once: setup (run once) + test_command (run each time)
    setup_script, test_command = parse_eval_script(eval_script)

    print("\n" + "=" * 60)
    print("SWE-BENCH TASK")
    print("=" * 60)
    print(f"Instance: {instance_id}")
    print(f"Docker image: {docker_image}")
    print("Test: SWE-bench eval script (setup + run tests; each run_tests re-runs the test block)")
    print(f"\nProblem:\n{problem_statement[:500]}...")
    if hints_text:
        print(f"\nHints:\n{hints_text[:300]}...")
    print("=" * 60 + "\n")

    mcp_url = f"http://localhost:{args.mcp_port}"
    container_id = None

    if not args.no_docker:
        print("Pulling Docker image...")
        if not docker_pull(docker_image):
            result = SolutionOutput(
                task_id=instance_id,
                benchmark="swebench",
                success=False,
                solution="",
                iterations=0,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_time_seconds=0,
                error="Docker pull failed",
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.model_dump_json(indent=2))
            sys.exit(1)

        print("Starting container...")
        mount_src = _PROJECT_ROOT.resolve()
        container_id = docker_run_container(docker_image, args.mcp_port, mount_src)
        if not container_id:
            result = SolutionOutput(
                task_id=instance_id,
                benchmark="swebench",
                success=False,
                solution="",
                iterations=0,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_time_seconds=0,
                error="Failed to start container",
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.model_dump_json(indent=2))
            sys.exit(1)

        print("Starting MCP server in container...")
        if not start_mcp_in_container(container_id, args.mcp_port):
            docker_stop(container_id)
            result = SolutionOutput(
                task_id=instance_id,
                benchmark="swebench",
                success=False,
                solution="",
                iterations=0,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_time_seconds=0,
                error="Failed to start MCP server",
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(result.model_dump_json(indent=2))
            sys.exit(1)

        print(f"MCP server at {mcp_url}")
    else:
        print(f"Using existing MCP server at {mcp_url}")

    try:
        # Verify MCP is reachable
        r = call_mcp_tool(mcp_url, "get_repo_tree", {"base_path": "/testbed"}, timeout=10)
        if not r["success"]:
            raise RuntimeError(f"MCP not reachable: {r.get('error', r.get('text', 'unknown'))}")

        system_prompt = """You are provided with a Github Repository. Based on information in Content (which is usually task/problem/assignment, and comments from devs regarding the problem) identify core issue, implement a minimal fix, run tests, and provide .diff patch as final_answer. Repo: /testbed.
Hard constraints:
- Avoid repeated exploration of the same symbols/files.
- Do not create ad-hoc scratch files/scripts for diagnosis.
- Maintain /testbed/ROOT.md as the authoritative running analysis and reference it when deciding edits.
- After every failed run_tests, call run_root_cause_analysis before any other tool.
- Use tools autonomously: get_repo_tree (first) -> focused search/read -> edit_file -> run_tests -> run_root_cause_analysis (on failures) -> get_patch."""

        # Normalize line endings (problem may have \r\n from Windows)
        problem_clean = problem_statement.replace("\r", "")
        hints_trunc = (hints_text[:800] + "...") if hints_text and len(hints_text) > 800 else (hints_text or "")

        user_prompt = f"""Problem:\n{problem_clean}\n{f'Hints: {hints_trunc}' if hints_trunc else ''}"""

        client = get_client(provider=args.provider, base_url=args.api_url, api_key=args.api_tokens)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        start = datetime.now()
        steps: list[StepMetrics] = []
        total_input = 0
        total_output = 0
        solution = ""
        success = False
        action_calls = 0
        run_test_calls = 0
        canonical_run_tests_done = False
        require_rca_after_failure = False
        last_failure_summary = ""
        last_failure_output = ""
        last_edit_file = ""
        consecutive_exploration_calls = 0
        tool_fingerprint_counts: dict[str, int] = {}
        edit_nudge_sent = False
        run_test_nudge_sent = False

        if args.log:
            log_path = args.log
        else:
            out_dir = args.output.parent
            existing = list(out_dir.glob("swebench_run-*.log"))
            nums = []
            for p in existing:
                try:
                    n = int(p.stem.split("-")[-1])
                    nums.append(n)
                except (ValueError, IndexError):
                    pass
            next_n = max(nums, default=0) + 1
            log_path = out_dir / f"swebench_run-{next_n}.log"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(f"SWE-bench run: {instance_id}\nStarted: {datetime.now().isoformat()}\n")

        def _log_step(iteration: int, direction: str, data: str):
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n--- Iteration {iteration} --- {direction}\n{'='*60}\n")
                f.write(data + "\n")

        def _write_root_md(content: str):
            call_mcp_tool(
                mcp_url,
                "write_file",
                {"base_path": "/testbed", "filepath": ROOT_FILEPATH, "content": content},
                timeout=20,
            )

        def _delete_root_md():
            call_mcp_tool(
                mcp_url,
                "delete_file",
                {"base_path": "/testbed", "filepath": ROOT_FILEPATH},
                timeout=20,
            )

        _write_root_md(
            "# ROOT ANALYSIS\n\n"
            "## Problem summary\n"
            f"{problem_clean[:3000]}\n\n"
            f"{('## Hints\n' + hints_trunc) if hints_trunc else ''}\n"
            "\n## Working notes\n- Initial analysis created by controller.\n"
        )

        for iteration in range(1, args.max_iterations + 1):
            if (datetime.now() - start).total_seconds() >= MAX_TIME_SECONDS:
                _delete_root_md()
                print("\nTimeout")
                break
            if total_input >= MAX_INPUT_TOKENS or total_output >= MAX_OUTPUT_TOKENS:
                _delete_root_md()
                print("\nToken limit exceeded")
                break

            print(f"\n--- Iteration {iteration} ---")
            # Truncate context: keep system + first user + last 10 msgs (5 turns) to reduce tokens
            if len(messages) > 12:
                messages = [messages[0], messages[1]] + messages[-10:]
            _log_step(iteration, "SENT", json.dumps({"messages": messages}, indent=2, default=str, ensure_ascii=False))
            print("  Calling LLM...", flush=True)
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    tools=SWEBENCH_TOOLS,
                    tool_choice="auto",
                    max_tokens=args.max_tokens,
                    timeout=args.llm_timeout,
                )
            except Exception as e:
                err = str(e)
                if "401" in err or "Unauthorized" in err or "<!DOCTYPE" in err:
                    print("LLM Error: 401 Unauthorized. Set HF_TOKEN (huggingface.co/settings/tokens) or use --provider ollama", file=sys.stderr)
                else:
                    print(f"LLM Error: {e}", file=sys.stderr)
                result = SolutionOutput(
                    task_id=instance_id,
                    benchmark="swebench",
                    success=False,
                    solution=solution or "",
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

            usage = completion.usage or type("U", (), {"prompt_tokens": 0, "completion_tokens": 0})()
            total_input += getattr(usage, "prompt_tokens", 0) or 0
            total_output += getattr(usage, "completion_tokens", 0) or 0

            choice = completion.choices[0]
            msg = choice.message
            resp_data = {"content": msg.content, "tool_calls": [{"name": tc.function.name, "args": tc.function.arguments} for tc in (msg.tool_calls or [])]}
            _log_step(iteration, "RECV", json.dumps(resp_data, indent=2, ensure_ascii=False))
            steps.append(StepMetrics(
                step=iteration,
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                request_time_ms=round((datetime.now() - start).total_seconds() * 1000, 1),
                timestamp=datetime.now().isoformat(),
            ))

            def _tc_dict(tc):
                return {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments or "{}"},
                }

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [_tc_dict(tc) for tc in (msg.tool_calls or [])],
            })

            if not msg.tool_calls:
                # No tool calls - only accept actual unified diff, not generic text with "patch"
                if msg.content and "diff --git" in msg.content and "---" in msg.content:
                    solution = msg.content
                # Nudge: some models return text instead of tool calls; prompt to continue
                elif not solution and not success:
                    print(f"  No tool calls (model returned text). Nudging...", flush=True)
                    messages.append({
                        "role": "user",
                        "content": "Follow the flow: get_repo_tree -> find_relevant/search_symbol -> read_file -> edit_file -> run_tests -> run_root_cause_analysis on failure.",
                    })
                    continue
                else:
                    break

            for tc in msg.tool_calls or []:
                name = tc.function.name
                try:
                    args_dict = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args_dict = {}
                args_dict.setdefault("base_path", "/testbed")
                if require_rca_after_failure and name != "run_root_cause_analysis":
                    blocked_text = (
                        "Controller: run_tests failed. You must call run_root_cause_analysis next "
                        "with failure_summary/output before any other tool."
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": blocked_text,
                    })
                    print(f"  {name}: blocked (RCA required)")
                    _log_step(iteration, f"TOOL {name}", f"args={args_dict}\nresult={blocked_text}")
                    continue
                if name == "run_root_cause_analysis":
                    args_dict.setdefault("failure_summary", last_failure_summary)
                    args_dict.setdefault("output", last_failure_output)
                    args_dict.setdefault("last_edit_file", last_edit_file)
                if name == "run_tests":
                    requested_eval = str(args_dict.get("eval_script") or "").strip()
                    requested_custom = bool(requested_eval) and requested_eval != eval_script.strip()
                    # Ensure one canonical run happens first (environment/setup), then allow custom reruns.
                    if not canonical_run_tests_done:
                        args_dict["eval_script"] = eval_script
                        if setup_script is not None and test_command is not None:
                            args_dict["setup_script"] = setup_script
                            args_dict["test_command"] = test_command
                    else:
                        if requested_custom:
                            args_dict["eval_script"] = _normalize_custom_eval_script(requested_eval)
                            # Do not inject setup/test blocks for custom commands.
                            args_dict.pop("setup_script", None)
                            args_dict.pop("test_command", None)
                        else:
                            args_dict["eval_script"] = eval_script
                            if setup_script is not None and test_command is not None:
                                args_dict["setup_script"] = setup_script
                                args_dict["test_command"] = test_command
                if name == "list_files":
                    d = args_dict.get("directory") or "."
                    if not d or d.startswith("/") or ".." in d:
                        args_dict["directory"] = "."
                if name == "search_code" and not args_dict.get("pattern"):
                    args_dict["pattern"] = "def |class "
                fp = f"{name}:{json.dumps(args_dict, sort_keys=True, default=str)}"
                tool_fingerprint_counts[fp] = tool_fingerprint_counts.get(fp, 0) + 1
                mcp_timeout = 600 if name == "run_tests" else 30
                result = call_mcp_tool(mcp_url, name, args_dict, timeout=mcp_timeout)
                text = result["text"] if result["success"] else f"Error: {result.get('error', result['text'])}"
                llm_text = _compact_tool_payload(name, text)
                parsed = None
                if name == "run_tests":
                    try:
                        parsed = json.loads(text)
                    except Exception:
                        parsed = None
                    if isinstance(parsed, dict):
                        compact = {
                            "success": parsed.get("success"),
                            "message": parsed.get("message"),
                        }
                        if parsed.get("success"):
                            compact["patch"] = "(diff available)" if parsed.get("patch") and parsed.get("patch") != "(no changes)" else "(no changes)"
                        else:
                            if parsed.get("failure_summary"):
                                compact["failure_summary"] = parsed.get("failure_summary")
                            if parsed.get("output"):
                                compact["failure_output"] = _extract_actionable_failure_output(str(parsed.get("output", "")))
                            compact["patch"] = "(diff available)" if parsed.get("patch") and parsed.get("patch") != "(no changes)" else "(no changes)"
                        llm_text = json.dumps(compact, ensure_ascii=False)
                if tool_fingerprint_counts[fp] >= 3 and name in EXPLORATION_TOOLS:
                    llm_text += "\n\n[controller-hint] This exact exploration call has repeated multiple times. Move to edit_file or run_tests now."
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": llm_text,
                })
                err_msg = "" if result["success"] else f" ({result.get('error', result.get('text', ''))[:100]})"
                display_ok = result["success"]
                if name == "run_tests" and isinstance(parsed, dict):
                    display_ok = bool(parsed.get("success"))
                print(f"  {name}: {'ok' if display_ok else 'fail'}{err_msg}")
                _log_step(iteration, f"TOOL {name}", f"args={args_dict}\nresult={text}")
                if name in ACTION_TOOLS:
                    action_calls += 1
                if name == "run_tests":
                    run_test_calls += 1
                if name == "edit_file":
                    last_edit_file = str(args_dict.get("filepath") or "")
                if name in EXPLORATION_TOOLS:
                    consecutive_exploration_calls += 1
                else:
                    consecutive_exploration_calls = 0
                if name == "get_patch" and result["success"]:
                    _delete_root_md()
                    solution = result["text"]
                    if solution and "diff --git" in solution:
                        success = True
                        print("  Got patch")
                if name == "run_root_cause_analysis" and result["success"]:
                    require_rca_after_failure = False
                    try:
                        rca = json.loads(result["text"])
                    except Exception:
                        rca = {"summary": result["text"]}
                    rca_text = (
                        "# ROOT ANALYSIS\n\n"
                        "## Problem summary\n"
                        f"{problem_clean[:3000]}\n\n"
                        f"{('## Hints\n' + hints_trunc + '\n\n') if hints_trunc else ''}"
                        "## Latest root-cause analysis\n"
                        f"{json.dumps(rca, indent=2, ensure_ascii=False)}\n"
                    )
                    _write_root_md(rca_text)
                if name == "run_tests" and result["success"]:
                    try:
                        r = json.loads(result["text"])
                        if r.get("success"):
                            _delete_root_md()
                            success = True
                            print("  Tests passed!")
                            # Use patch from run_tests (captured before eval script ran; eval may revert files)
                            if not solution:
                                solution = r.get("patch", "") or "(no changes)"
                                print("  Got patch (auto)" if "diff --git" in solution else "  Got patch (no diff)")
                                break  # break from tool_calls loop, then exit iteration loop below
                        else:
                            require_rca_after_failure = True
                            last_failure_summary = str(r.get("failure_summary") or "")
                            last_failure_output = str(r.get("output") or "")
                            failed_tests = _extract_failed_tests_from_summary(last_failure_summary)
                            actionable = _extract_actionable_failure_output(last_failure_output)
                            analyze_lines = [
                                "Controller directive: Analyze test failure and propose root cause now.",
                            ]
                            if failed_tests:
                                analyze_lines.append(f"Failing tests: {', '.join(failed_tests)}")
                            if last_failure_summary:
                                analyze_lines.append(f"failure_summary:\n{last_failure_summary[:3000]}")
                            if actionable:
                                analyze_lines.append(f"failure_output:\n{actionable[:6000]}")
                            analyze_lines.append(
                                "Next step must be run_root_cause_analysis, then implement edit_file from that analysis."
                            )
                            messages.append({
                                "role": "user",
                                "content": "\n\n".join(analyze_lines),
                            })
                    except Exception:
                        pass

            if not success:
                if not edit_nudge_sent and action_calls == 0 and iteration in (10, 14):
                    messages.append({
                        "role": "user",
                        "content": "Controller: Stop exploring. Implement a concrete edit now (edit_file), then run_tests.",
                    })
                    edit_nudge_sent = True
                if not run_test_nudge_sent and run_test_calls == 0 and iteration >= 18:
                    messages.append({
                        "role": "user",
                        "content": "Controller: You must run run_tests now. Do not continue searching.",
                    })
                    run_test_nudge_sent = True
                if consecutive_exploration_calls >= 6:
                    messages.append({
                        "role": "user",
                        "content": "Controller: Repeated exploration detected. Pick one file, apply edit_file, and run_tests.",
                    })
                    consecutive_exploration_calls = 0

            # Exit outer loop when we have solution after tests passed
            if success and solution:
                break

        elapsed = (datetime.now() - start).total_seconds()
        result = SolutionOutput(
            task_id=instance_id,
            benchmark="swebench",
            success=success,
            solution=solution or "",
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
        print(f"Log: {log_path}")
        print(f"Success: {success}")
        print("=" * 60)

    finally:
        try:
            if 'mcp_url' in locals():
                call_mcp_tool(
                    mcp_url,
                    "delete_file",
                    {"base_path": "/testbed", "filepath": ROOT_FILEPATH},
                    timeout=10,
                )
        except Exception:
            pass
        if container_id:
            print("Stopping container...")
            docker_stop(container_id)


if __name__ == "__main__":
    main()
