#!/usr/bin/env python3
"""SWE-bench MCP tools server (stdio). Exposes mandatory tools."""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.tools.filesystem import read_file, edit_file, list_files
from agent_smith.tools.code_search import (
    search_code,
    search_function_or_class_definition_in_code,
    find_references,
)
from agent_smith.tools.execution import run_tests, get_patch


def main():
    base = Path(os.environ.get("MCP_WORKDIR", "."))
    eval_script = os.environ.get("MCP_EVAL_SCRIPT", "python -m pytest")

    def read_file_tool(filepath: str, start_line: int, end_line: int):
        return read_file(filepath, start_line, end_line, base)

    def edit_file_tool(filepath: str, old_str: str, new_str: str):
        return edit_file(filepath, old_str, new_str, base)

    def list_files_tool(directory: str, pattern: str):
        return list_files(directory, pattern, base)

    def search_code_tool(pattern: str, file_pattern: str = "*.py"):
        return search_code(pattern, file_pattern, base)

    def search_def_tool(name: str):
        return search_function_or_class_definition_in_code(name, base)

    def find_refs_tool(name: str, filepath: str, line: int):
        return find_references(name, filepath, line, base)

    def run_tests_tool():
        return run_tests(eval_script, base)

    def get_patch_tool():
        return get_patch(base)

    tools = {
        "read_file": read_file_tool,
        "edit_file": edit_file_tool,
        "list_files": list_files_tool,
        "search_code": search_code_tool,
        "search_function_or_class_definition_in_code": search_def_tool,
        "find_references": find_refs_tool,
        "run_tests": run_tests_tool,
        "get_patch": get_patch_tool,
    }

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method", "")
            params = req.get("params", {})
            if method in tools:
                result = tools[method](**params)
                print(json.dumps({"result": result}), flush=True)
            else:
                print(json.dumps({"error": f"Unknown method: {method}"}), flush=True)
        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    main()
