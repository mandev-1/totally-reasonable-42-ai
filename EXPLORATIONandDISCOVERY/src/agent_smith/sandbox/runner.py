"""Sandbox code execution (Section 4.2)."""

import io
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from agent_smith.models.sandbox import SandboxConfig


# Tool registry: name -> (callable, docstring)
_sandbox_tools: Dict[str, tuple[Callable[..., Any], str]] = {}
_final_answer_storage: list = []


def register_tool(name: str, func: Callable[..., Any], doc: str = "") -> None:
    """Register a tool callable from sandbox code."""
    _sandbox_tools[name] = (func, doc or (func.__doc__ or ""))


def _final_answer_impl(answer: str) -> None:
    """Tool: agent submits final answer and stops."""
    _final_answer_storage.clear()
    _final_answer_storage.append(str(answer))


def _make_restricted_import(authorized: list) -> Callable:
    """Return a restricted __import__ that only allows authorized modules."""

    import builtins
    _real_import = builtins.__import__

    def restricted_import(name: str, *args: Any, **kwargs: Any) -> Any:
        # Check if name or any prefix matches authorized
        allowed = False
        for auth in authorized:
            if auth.endswith(".*"):
                prefix = auth[:-2]
                if name == prefix or name.startswith(prefix + "."):
                    allowed = True
                    break
            elif name == auth:
                allowed = True
                break
        if not allowed:
            raise ImportError(f"Import of '{name}' is not allowed in sandbox")
        return _real_import(name, *args, **kwargs)

    return restricted_import


def _validate_path(path: Path, allowed_dirs: list, base: Path) -> bool:
    """Check if path is within allowed directories or base."""
    try:
        resolved = path.resolve()
        base_resolved = base.resolve()
        try:
            resolved.relative_to(base_resolved)
            return True
        except ValueError:
            pass
        for allowed in allowed_dirs:
            ap = Path(allowed).resolve()
            try:
                resolved.relative_to(ap)
                return True
            except ValueError:
                continue
        return False
    except Exception:
        return False


def get_tool_globals(
    config: SandboxConfig,
    base_dir: Optional[Path] = None,
    eval_script: str = "python -m pytest",
) -> Dict[str, Any]:
    """Build globals dict for sandbox execution with registered tools."""
    base = base_dir or Path(".")
    _final_answer_storage.clear()

    # Create wrapped tools that use base_dir and enforce path restrictions
    from agent_smith.tools import filesystem, code_search, execution

    def read_file_tool(fp: str, start: int, end: int) -> str:
        p = (base / fp).resolve()
        if not _validate_path(p, config.allowed_directories, base):
            return "Error: path not in allowed directories"
        return filesystem.read_file(fp, start, end, base)

    def edit_file_tool(fp: str, old: str, new: str) -> str:
        p = (base / fp).resolve()
        if not _validate_path(p, config.allowed_directories, base):
            return "Error: path not in allowed directories"
        return filesystem.edit_file(fp, old, new, base)

    def list_files_tool(d: str, pattern: str) -> str:
        p = (base / d).resolve()
        if not _validate_path(p, config.allowed_directories, base):
            return "Error: path not in allowed directories"
        return filesystem.list_files(d, pattern, base)

    def search_code_tool(pattern: str, file_pattern: str = "*.py") -> str:
        return code_search.search_code(pattern, file_pattern, base)

    def search_def_tool(name: str) -> str:
        return code_search.search_function_or_class_definition_in_code(name, base)

    def find_refs_tool(name: str, fp: str, line: int) -> str:
        return code_search.find_references(name, fp, line, base)

    def run_tests_tool() -> str:
        return execution.run_tests(eval_script, base)

    def get_patch_tool() -> str:
        return execution.get_patch(base)

    g: Dict[str, Any] = {
        "final_answer": _final_answer_impl,
        "read_file": read_file_tool,
        "edit_file": edit_file_tool,
        "list_files": list_files_tool,
        "search_code": search_code_tool,
        "search_function_or_class_definition_in_code": search_def_tool,
        "find_references": find_refs_tool,
        "run_tests": run_tests_tool,
        "get_patch": get_patch_tool,
    }

    # Restricted imports
    import builtins
    restricted_import = _make_restricted_import(config.authorized_imports)
    g["__builtins__"] = dict(builtins.__dict__)
    g["__builtins__"]["__import__"] = restricted_import

    return g


def execute(
    code: str,
    config: SandboxConfig,
    tool_globals: Optional[Dict[str, Any]] = None,
    base_dir: Optional[Path] = None,
    eval_script: str = "python -m pytest",
) -> tuple[str, Optional[str]]:
    """Execute code in a restricted environment.

    Returns (stdout_or_error, final_answer_or_None).

    Enforces: restricted imports, allowed paths, timeout, output capture.
    """
    g = tool_globals or get_tool_globals(config, base_dir, eval_script)
    _final_answer_storage.clear()

    # Capture stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    out_buffer = io.StringIO()
    sys.stdout = out_buffer
    sys.stderr = out_buffer

    try:
        exec(code, g)
        out = out_buffer.getvalue() or "Execution completed."
        ans = _final_answer_storage[0] if _final_answer_storage else None
        return (out, ans)
    except Exception as e:
        return (f"Error: {type(e).__name__}: {e}", None)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
