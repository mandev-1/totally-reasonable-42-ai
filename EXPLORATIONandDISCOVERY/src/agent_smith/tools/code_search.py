"""Code search tools (Section 4.5.2)."""

import re
from pathlib import Path
from typing import List, Optional, Tuple


def _search(
    base_dir: Path,
    pattern: str,
    file_pattern: str = "*.py",
) -> List[Tuple[str, int, str]]:
    """Grep-like search. Returns [(path, line_num, line_content), ...]."""
    results: List[Tuple[str, int, str]] = []
    try:
        regex = re.compile(pattern)
    except re.error:
        return [(f"Error: invalid regex '{pattern}'", 0, "")]
    for f in base_dir.rglob(file_pattern):
        if not f.is_file():
            continue
        try:
            for i, line in enumerate(f.read_text().splitlines(), 1):
                if regex.search(line):
                    results.append((str(f.resolve()), i, line))
        except Exception:
            pass
    return results


def _format_results(results: List[Tuple[str, int, str]]) -> str:
    """Format as /path/to/file.py:<line> <content>"""
    return "\n".join(f"{p}:{n} {c}" for p, n, c in results)


def search_code(
    pattern: str,
    file_pattern: str = "*.py",
    base_dir: Optional[Path] = None,
) -> str:
    """Perform a grep-like search in the codebase."""
    base = base_dir or Path(".")
    return _format_results(_search(base, pattern, file_pattern))


def search_function_or_class_definition_in_code(
    name: str,
    base_dir: Optional[Path] = None,
) -> str:
    """Find the definition of a function or a class."""
    base = base_dir or Path(".")
    pattern = rf"^\s*(def|class)\s+{re.escape(name)}\s*[:(]"
    return _format_results(_search(base, pattern, "*.py"))


def find_references(
    name: str,
    filepath: str,
    line: int,
    base_dir: Optional[Path] = None,
) -> str:
    """Find all usages of a symbol (function or class)."""
    base = base_dir or Path(".")
    pattern = rf"\b{re.escape(name)}\b"
    return _format_results(_search(base, pattern, "*.py"))
