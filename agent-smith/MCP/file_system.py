"""File system tools for SWE-bench MCP."""
import fnmatch
import os
from pathlib import Path


def _resolve_path(base_path: str, filepath: str) -> Path:
    """Resolve filepath relative to base_path, ensure it stays under base."""
    base = Path(base_path).resolve()
    resolved = (base / filepath).resolve()
    if not str(resolved).startswith(str(base)):
        raise ValueError(f"Path {filepath} escapes base {base_path}")
    return resolved


def read_file(base_path: str, filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
    """
    Read file content with line numbers (cat -n format).

    Output format: <line_number>: <line_content>
    """
    path = _resolve_path(base_path, filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not path.is_file():
        raise ValueError(f"Not a file: {path}")

    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    start = (start_line or 1) - 1
    end = end_line or len(lines)
    start = max(0, min(start, len(lines)))
    end = max(start, min(end, len(lines)))

    result = []
    for i in range(start, end):
        result.append(f"{i + 1}: {lines[i]}")
    return "\n".join(result)


def write_file(base_path: str, filepath: str, content: str) -> str:
    """Create or overwrite file with content. Returns 'ok' on success."""
    path = _resolve_path(base_path, filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return "ok"


def delete_file(base_path: str, filepath: str) -> str:
    """Delete file if it exists. Returns 'ok' on success."""
    path = _resolve_path(base_path, filepath)
    if path.exists() and path.is_file():
        path.unlink()
    return "ok"


def edit_file(base_path: str, filepath: str, old_str: str, new_str: str) -> str:
    """Replace exact string in file. Returns 'ok' on success."""
    path = _resolve_path(base_path, filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    content = path.read_text(encoding="utf-8", errors="replace")
    if old_str not in content:
        raise ValueError("old_str not found in file")
    new_content = content.replace(old_str, new_str, 1)
    path.write_text(new_content, encoding="utf-8")
    return "ok"


def get_repo_tree(base_path: str, max_depth: int = 4, max_lines: int = 400) -> str:
    """
    Return tree structure of repo for scoping. Excludes .git, __pycache__, *.pyc.
    Use this FIRST to pick which files to read - avoid blind search.
    """
    base = Path(base_path).resolve()
    if not base.exists():
        raise FileNotFoundError(f"Base path not found: {base}")

    SKIP = {".git", "__pycache__", ".venv", "venv", "node_modules", ".tox", "dist", "build", "doc", "docs", "*.pyc"}
    # Prioritize source dirs (sympy, src, lib) so they appear before doc/, .ci, etc.
    SOURCE_FIRST = {"sympy", "src", "lib", "source"}

    def _tree(path: Path, prefix: str, depth: int, lines: list[str]) -> None:
        if depth > max_depth or len(lines) >= max_lines:
            return
        try:
            entries = list(path.iterdir())
        except PermissionError:
            return
        dirs = [e for e in entries if e.is_dir() and e.name not in SKIP and not e.name.endswith(".pyc")]
        files = [e for e in entries if e.is_file() and not (e.name.endswith(".pyc") or e.suffix == ".pyc")]
        # Put source-like dirs first so they appear before truncation
        dirs.sort(key=lambda e: (e.name not in SOURCE_FIRST, e.name.lower()))
        files.sort(key=lambda e: e.name.lower())
        entries = dirs + files
        for i, entry in enumerate(entries):
            is_last = i == len(entries) - 1
            conn = "└── " if is_last else "├── "
            lines.append(prefix + conn + entry.name)
            if entry.is_dir() and entry.name not in SKIP:
                ext = "    " if is_last else "│   "
                _tree(entry, prefix + ext, depth + 1, lines)

    lines = []
    _tree(base, "", 0, lines)
    out = "\n".join(lines[:max_lines])
    if len(lines) > max_lines:
        out += f"\n... (truncated, {len(lines) - max_lines} more lines)"
    return out or "(empty)"


def list_files(base_path: str, directory: str = ".", pattern: str = "*") -> str:
    """List files in directory matching pattern. Returns newline-separated paths."""
    base = Path(base_path).resolve()
    dir_path = (base / directory).resolve()
    if not str(dir_path).startswith(str(base)):
        raise ValueError(f"Directory {directory} escapes base {base_path}")
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {dir_path}")
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {dir_path}")

    results = []
    for root, _, files in os.walk(dir_path):
        rel_root = Path(root).relative_to(base)
        for f in files:
            if fnmatch.fnmatch(f, pattern):
                results.append(str(rel_root / f))
    return "\n".join(sorted(results))
