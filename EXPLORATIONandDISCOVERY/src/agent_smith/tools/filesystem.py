"""File system tools (Section 4.5.1)."""

import fnmatch
from pathlib import Path
from typing import List, Optional


def read_file(
    filepath: str,
    start_line: int,
    end_line: int,
    base_dir: Optional[Path] = None,
) -> str:
    """Read the content of a file with line numbers.

    Output format similar to cat -n:
    <line_number>: <line_content>
    """
    base = base_dir or Path(".")
    path = (base / filepath).resolve()
    if not path.exists():
        return f"Error: file not found: {filepath}"
    try:
        lines = path.read_text().splitlines()
    except Exception as e:
        return f"Error reading file: {e}"
    result = []
    for i in range(max(0, start_line - 1), min(len(lines), end_line)):
        result.append(f"{i + 1}: {lines[i]}")
    return "\n".join(result)


def edit_file(
    filepath: str,
    old_str: str,
    new_str: str,
    base_dir: Optional[Path] = None,
) -> str:
    """Replace an exact string in a file with a new string."""
    base = base_dir or Path(".")
    path = (base / filepath).resolve()
    if not path.exists():
        return f"Error: file not found: {filepath}"
    try:
        content = path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"
    if old_str not in content:
        return f"Error: old_str not found in {filepath}"
    new_content = content.replace(old_str, new_str, 1)
    try:
        path.write_text(new_content)
    except Exception as e:
        return f"Error writing file: {e}"
    return "OK"


def list_files(
    directory: str,
    pattern: str,
    base_dir: Optional[Path] = None,
) -> str:
    """List files in a directory matching a given pattern."""
    base = base_dir or Path(".")
    path = (base / directory).resolve()
    if not path.is_dir():
        return f"Error: {directory} is not a directory"
    results: List[str] = []
    for p in path.rglob("*"):
        if p.is_file() and fnmatch.fnmatch(p.name, pattern):
            try:
                rel = p.relative_to(path)
                results.append(str(rel))
            except ValueError:
                results.append(p.name)
    return "\n".join(sorted(results))
