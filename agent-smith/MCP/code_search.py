"""Code search tools for SWE-bench MCP."""
import re
from pathlib import Path


def _resolve_base(base_path: str) -> Path:
    return Path(base_path).resolve()


def _format_match(filepath: Path, line_num: int, content: str) -> str:
    return f"{filepath}:{line_num} {content}"


def search_code(base_path: str, pattern: str, file_pattern: str = "*.py") -> str:
    """
    Perform grep-like search in the entire codebase. Output format: /absolute/path/file.py:line_number line_content
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


def find_relevant(
    base_path: str,
    keywords: str,
    max_files: int = 5,
    context_lines: int = 5,
) -> str:
    """
    One-shot focused search. Pass space/comma-separated keywords from the problem
    (e.g. "session headers Accept-Encoding"). Returns top matching files with
    surrounding context. Use this FIRST instead of many search_code + read_file calls.
    """
    base = _resolve_base(base_path)
    if not base.exists():
        raise FileNotFoundError(f"Base path not found: {base}")

    # Extract search terms (alphanumeric + underscore)
    terms = [
        t.strip()
        for t in re.split(r"[\s,]+", keywords)
        if t.strip() and len(t.strip()) > 1
    ]
    if not terms:
        return "No keywords provided. Pass terms like: session headers Accept-Encoding"

    # Build regex: any of the terms (word boundaries)
    pattern = re.compile(
        "|".join(rf"\b{re.escape(t)}\b" for t in terms[:8]),
        re.IGNORECASE,
    )

    # Collect matches with context: (filepath, line_num, score, lines_with_context)
    matches: list[tuple[Path, int, int, list[str]]] = []
    for path in base.rglob("*.py"):
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        try:
            rel_path = path.relative_to(base)
        except ValueError:
            rel_path = path.name
        for i, line in enumerate(lines):
            if pattern.search(line):
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = [f"{j+1}: {lines[j]}" for j in range(start, end)]
                score = sum(1 for t in terms if t.lower() in line.lower())
                matches.append((Path(rel_path), i + 1, score, context))

    # Sort by score desc, then by file (group by file)
    matches.sort(key=lambda m: (-m[2], str(m[0]), m[1]))

    # Dedupe by file, keep top matches per file
    seen_files: set[str] = set()
    results: list[str] = []
    for path, line_num, _score, context in matches:
        key = str(path)
        if key in seen_files:
            continue
        if len(seen_files) >= max_files:
            break
        seen_files.add(key)
        results.append(f"\n--- {path} (match at line {line_num}) ---\n" + "\n".join(context))

    return "\n".join(results) if results else f"No matches for: {keywords}"


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
