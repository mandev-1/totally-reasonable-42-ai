#!/usr/bin/env python3
"""MBPP MCP tools server (stdio). Exposes run_tests for MBPP benchmark."""

import json
import sys
import os
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_smith.tools.execution import run_tests


def main():
    """Simple stdio server: read JSON-RPC, dispatch to tools, write response."""
    base = Path(os.environ.get("MCP_WORKDIR", "."))
    eval_script = os.environ.get("MCP_EVAL_SCRIPT", "python -m pytest")

    def handle_run_tests():
        return run_tests(eval_script, base)

    tools = {"run_tests": handle_run_tests}

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
