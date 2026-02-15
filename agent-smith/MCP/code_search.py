"""Code search tools for SWE-bench MCP."""
import re
from pathlib import Path


def _resolve_base(base_path: str) -> Path:
    return Path(base_path).resolve()


def _format_match(filepath: Path, line_num: int, content: str) -> str:
    return f"{filepath}:{line_num} {content}"


def search_code(base_path: str, pattern: str, file_pattern: str = "*.py") -> str:
    """
    Grep-like search. Output format: /absolute/path/file.py:line_number line_content
    """
    base = _resolve_base(base_path)
    if not base.exists():
        raise FileNotFoundError(f"Base path not found: {base}")

    regex = re.compile(pattern)
    results = []
    for path in base.rglob(file_pattern):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        abs_path = path.resolve()
        for i, line in enumerate(text.splitlines(), 1):
            if regex.search(line):
                results.append(_format_match(abs_path, i, line))
    return "\n".join(results)


def search_function_or_class_definition_in_code(base_path: str, name: str) -> str:
    """Find definition of function or class. Same output format as search_code."""
    base = _resolve_base(base_path)
    if not base.exists():
        raise FileNotFoundError(f"Base path not found: {base}")

    # Match: def name( or class name(
    pattern = re.compile(rf"^\s*(def|class)\s+{re.escape(name)}\s*[\(:]")
    results = []
    for path in base.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        abs_path = path.resolve()
        for i, line in enumerate(text.splitlines(), 1):
            if pattern.match(line):
                results.append(_format_match(abs_path, i, line))
    return "\n".join(results)


def find_references(base_path: str, name: str, filepath: str, line: int) -> str:
    """Find usages of symbol (function or class). Same output format as search_code."""
    base = _resolve_base(base_path)
    # Word boundary search for the name
    pattern = re.compile(rf"\b{re.escape(name)}\b")
    results = []
    for path in base.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        abs_path = path.resolve()
        for i, content in enumerate(text.splitlines(), 1):
            if pattern.search(content):
                results.append(_format_match(abs_path, i, content))
    return "\n".join(results)
