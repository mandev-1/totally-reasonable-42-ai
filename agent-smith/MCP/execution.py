"""Execution tools for SWE-bench MCP."""
import re
import subprocess
import tempfile
from pathlib import Path

# Per-process: setup run once per container (MCP server lifetime)
_setup_done = False


# Minimal header for test_block (fresh subprocess needs env + cwd)
_TEST_BLOCK_HEADER = """#!/bin/bash
set -eo pipefail
source /opt/miniconda3/bin/activate 2>/dev/null || true
conda activate testbed 2>/dev/null || true
cd /testbed
"""


def _normalize_test_command(command: str) -> str:
    """Normalize common short test commands into runnable shell commands."""
    cmd = (command or "").strip()
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


def _wrap_single_test_command(script: str) -> str:
    """Run one-liner custom test commands inside activated testbed env."""
    s = (script or "").strip()
    if not s:
        return s
    if "\n" in s or s.startswith("#!"):
        return script
    return _TEST_BLOCK_HEADER + _normalize_test_command(s) + "\n"


def parse_eval_script(eval_script: str) -> tuple[str | None, str | None]:
    """
    Parse SWE-bench eval_script into setup (run once) and test_command (run each time).
    Returns (setup_script, test_command). If unparseable, returns (None, None).
    Caller should fall back to full eval_script when both are None.
    """
    result = _split_eval_script(eval_script)
    return result if result else (None, None)


def _split_eval_script(eval_script: str) -> tuple[str, str] | None:
    """
    Split SWE-bench eval_script into setup (run once) and test_block (run each time).
    Setup = everything through pip install (the slow part).
    Test_block = git checkout, git apply, test run, teardown (fast).
    Returns (setup, test_block) or None if unparseable.
    """
    lines = eval_script.splitlines()
    setup_lines = []
    test_lines = []
    found_split = False

    for line in lines:
        if not found_split and "pip install" in line.lower():
            setup_lines.append(line)
            found_split = True
            continue
        if found_split:
            test_lines.append(line)
        else:
            setup_lines.append(line)

    if not found_split or not test_lines:
        return None
    test_block = _TEST_BLOCK_HEADER + "\n".join(test_lines)
    return ("\n".join(setup_lines), test_block)


def _run_script(base: Path, script: str, timeout: int) -> dict:
    """Run a bash script in the testbed. Returns {success, output, message}."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        Path(script_path).chmod(0o755)
        result = subprocess.run(
            ["/bin/bash", script_path],
            cwd=str(base),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        # Some SWE-bench eval scripts do not use `set -e`, so pytest can fail
        # while later commands still produce an overall zero exit code.
        if success and _has_pytest_failures(output):
            success = False
        return {
            "success": success,
            "output": output,
            "message": "Tests passed" if success else "Tests failed",
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": f"Execution timed out after {timeout} seconds",
            "message": "Timeout",
        }
    except Exception as e:
        return {"success": False, "output": str(e), "message": "Execution error"}
    finally:
        Path(script_path).unlink(missing_ok=True)


def run_python_snippet(base_path: str, code: str, timeout: int = 60) -> dict:
    """
    Run a short Python snippet inside testbed env for cheap introspection.
    Prefer this over full run_tests for print/debug exploration.
    """
    if not code.strip():
        return {"success": False, "output": "Empty code", "message": "Invalid snippet"}
    base = Path(base_path).resolve()
    if not base.exists() or not base.is_dir():
        return {"success": False, "output": f"Invalid testbed path: {base}", "message": "Invalid testbed"}
    script = (
        _TEST_BLOCK_HEADER
        + "python - <<'PY'\n"
        + code
        + "\nPY\n"
    )
    r = _run_script(base, script, timeout)
    return {
        "success": bool(r.get("success")),
        "output": r.get("output", ""),
        "message": "Snippet executed" if r.get("success") else "Snippet failed",
    }


def _has_pytest_failures(output: str) -> bool:
    """Return True when pytest output clearly indicates failing tests."""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("FAILED "):
            return True
        # Example: "================== 2 failed, 117 passed ... =================="
        if re.search(r"\b\d+\s+failed\b", stripped):
            return True
    return False


def run_tests(
    base_path: str,
    eval_script: str,
    timeout: int = 1800,
    setup_script: str | None = None,
    test_command: str | None = None,
) -> dict:
    """
    Execute the evaluation script in the testbed.
    When setup_script and test_command are provided (pre-parsed by agent): use those.
    Otherwise parse eval_script internally.
    First call: runs full setup (incl. pip install) + test.
    Subsequent calls: runs only test block - skips pip install.
    """
    global _setup_done

    base = Path(base_path).resolve()
    if not base.exists():
        return {"success": False, "output": f"Testbed not found: {base}", "message": "Testbed not found"}
    if not base.is_dir():
        return {"success": False, "output": f"Not a directory: {base}", "message": "Invalid testbed"}

    # Use pre-parsed blocks if provided, else parse
    if setup_script is not None and test_command is not None:
        setup_block, test_block = setup_script, test_command
    else:
        split = _split_eval_script(eval_script)
        if split is None:
            patch = get_patch(str(base))
            r = _run_script(base, _wrap_single_test_command(eval_script), timeout)
            r["patch"] = patch
            return r
        setup_block, test_block = split

    # Capture patch BEFORE eval script runs (eval script may git checkout/revert files)
    patch = get_patch(str(base))

    if not _setup_done:
        # First run: full script (setup + test) - use eval_script for correct structure
        result = _run_script(base, eval_script, timeout)
        _setup_done = True
    else:
        # Subsequent runs: only test block (skip pip install)
        result = _run_script(base, test_block, timeout)

    if not result.get("success") and result.get("output"):
        result["failure_summary"] = _extract_failure_summary(result["output"])
    result["patch"] = patch
    return result


def _extract_failure_summary(output: str) -> str:
    """Extract pytest-style failure summary from test output."""
    lines = output.splitlines()
    summary = []
    for i, line in enumerate(lines):
        if "FAILED" in line:
            summary.append(line.strip())
        if "AssertionError" in line:
            summary.append(line.strip())
        if line.strip().startswith("E   ") and "assert" in line:
            summary.append(line.strip())
    if not summary:
        summary = [ln.strip() for ln in lines[-40:] if ln.strip()]
    return "\n".join(summary[:50])


def run_tests_with_failure_summary(
    base_path: str,
    eval_script: str,
    timeout: int = 1800,
    setup_script: str | None = None,
    test_command: str | None = None,
) -> dict:
    """Same as run_tests but with failure_summary when tests fail."""
    r = run_tests(base_path, eval_script, timeout, setup_script, test_command)
    if not r.get("success") and r.get("output"):
        r["failure_summary"] = _extract_failure_summary(r["output"])
    return r


def validate_patch(base_path: str, patch_text: str) -> dict:
    """Validate patch format. Returns {valid, message}."""
    if not patch_text or patch_text.strip() == "(no changes)":
        return {"valid": False, "message": "Empty or no changes"}
    if "diff --git" not in patch_text:
        return {"valid": False, "message": "Not a valid unified diff (missing 'diff --git')"}
    if "---" not in patch_text or "+++" not in patch_text:
        return {"valid": False, "message": "Missing ---/+++ headers"}
    return {"valid": True, "message": "Valid unified diff format"}


def get_patch(base_path: str) -> str:
    """Retrieve unified git diff of all changes (SWE-bench format: core.fileMode=false)."""
    base = Path(base_path).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Testbed not found: {base}")

    result = subprocess.run(
        ["git", "-c", "core.fileMode=false", "diff"],
        cwd=str(base),
        capture_output=True,
        text=True,
    )
    return result.stdout or "(no changes)"


def run_root_cause_analysis(
    base_path: str,
    failure_summary: str,
    output: str = "",
    last_edit_file: str = "",
) -> dict:
    """
    Build structured RCA from failed test output and cite likely code locations.
    """
    base = Path(base_path).resolve()
    text = "\n".join([failure_summary or "", output or ""])

    failing_tests = []
    for line in (failure_summary or "").splitlines():
        s = line.strip()
        if s.startswith("FAILED "):
            failing_tests.append(s.replace("FAILED ", "", 1))
    failing_tests = failing_tests[:5]

    evidence_lines = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("FAILED ") or "AssertionError" in s or s.startswith("E   "):
            evidence_lines.append(s)
    evidence_lines = evidence_lines[:15]

    ref_matches = re.findall(r"([A-Za-z0-9_./-]+\.py):(\d+)", text)
    seen_refs = set()
    code_citations = []
    for rel_file, ln_s in ref_matches:
        key = (rel_file, ln_s)
        if key in seen_refs:
            continue
        seen_refs.add(key)
        try:
            line_no = int(ln_s)
        except ValueError:
            continue
        fpath = (base / rel_file).resolve()
        if not str(fpath).startswith(str(base)) or not fpath.exists():
            continue
        try:
            lines = fpath.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        start = max(1, line_no - 2)
        end = min(len(lines), line_no + 2)
        snippet = "\n".join(f"{i}: {lines[i-1]}" for i in range(start, end + 1))
        code_citations.append(
            {
                "file": rel_file,
                "line": line_no,
                "snippet": snippet,
            }
        )
        if len(code_citations) >= 3:
            break

    if last_edit_file:
        likely = f"Most likely caused by recent edits in {last_edit_file}; verify logic against failing assertion."
    elif code_citations:
        likely = f"Most likely caused by logic near {code_citations[0]['file']}:{code_citations[0]['line']}."
    else:
        likely = "Likely caused by behavior mismatch between expected and inferred return conditions."

    suspected_return_path = ""
    trigger_condition = ""
    if code_citations:
        first = code_citations[0]
        suspected_return_path = f"{first['file']}:{first['line']}"
    if evidence_lines:
        trigger_condition = evidence_lines[0]

    return {
        "summary": likely,
        "failing_tests": failing_tests,
        "evidence": evidence_lines,
        "code_citations": code_citations,
        "suspected_return_path": suspected_return_path or "unknown (inspect nearest return branch)",
        "trigger_condition": trigger_condition or "unknown (inspect guard that produced wrong boolean)",
        "next_action": "Apply a focused edit_file change at cited location, then run_tests.",
    }
