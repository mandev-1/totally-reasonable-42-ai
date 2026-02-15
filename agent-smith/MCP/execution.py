"""Execution tools for SWE-bench MCP."""
import subprocess
import tempfile
from pathlib import Path


def run_tests(base_path: str, eval_script: str, timeout: int = 1800) -> dict:
    """
    Execute the evaluation script in the testbed.
    Runs eval_script as bash with cwd=base_path.
    Returns {success, output, message}.
    """
    base = Path(base_path).resolve()
    if not base.exists():
        return {"success": False, "output": f"Testbed not found: {base}", "message": "Testbed not found"}
    if not base.is_dir():
        return {"success": False, "output": f"Not a directory: {base}", "message": "Invalid testbed"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sh", delete=False) as f:
        f.write(eval_script)
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


def get_patch(base_path: str) -> str:
    """Retrieve unified git diff of all changes in the repository."""
    base = Path(base_path).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Testbed not found: {base}")

    result = subprocess.run(
        ["git", "diff"],
        cwd=str(base),
        capture_output=True,
        text=True,
    )
    return result.stdout or "(no changes)"
