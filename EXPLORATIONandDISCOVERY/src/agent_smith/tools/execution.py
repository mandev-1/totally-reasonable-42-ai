"""Execution tools (Section 4.5.3)."""

import subprocess
from pathlib import Path
from typing import Optional


def run_tests(
    eval_script: str = "python -m pytest",
    cwd: Optional[Path] = None,
) -> str:
    """Execute the evaluation script."""
    cwd = cwd or Path(".")
    try:
        result = subprocess.run(
            eval_script,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=60,
        )
        out = result.stdout + result.stderr
        return f"exit_code={result.returncode}\n{out}"
    except subprocess.TimeoutExpired:
        return "Error: timeout"
    except Exception as e:
        return f"Error: {e}"


def get_patch(cwd: Optional[Path] = None) -> str:
    """Retrieve the unified git diff of all changes made to the repository."""
    cwd = cwd or Path(".")
    try:
        result = subprocess.run(
            ["git", "-c", "core.fileMode=false", "diff"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        return result.stdout or "(no changes)"
    except Exception as e:
        return f"Error: {e}"
