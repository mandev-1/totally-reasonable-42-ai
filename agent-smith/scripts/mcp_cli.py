#!/usr/bin/env python3
"""CLI for MCP servers. Usage: uv run mcp mbpp [--port 8765]"""
import sys
from pathlib import Path

# Add project root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run mcp <server> [options]")
        print("  mbpp     Start MBPP MCP server (run_tests tool)")
        print("           Default: http://localhost:8765")
        print("  swebench Start SWE-bench MCP server (file_system, code_search, execution)")
        print("           Default: http://localhost:8766")
        sys.exit(1)

    server = sys.argv[1].lower()
    args = sys.argv[2:]

    if server == "mbpp":
        from MCP.mbpp import main as mbpp_main
        if "--port" not in args and "-p" not in args:
            args = ["--port", "8765"] + args
        sys.argv = ["mcp"] + args
        mbpp_main()
    elif server == "swebench":
        from MCP.swebench import main as swebench_main
        if "--port" not in args and "-p" not in args:
            args = ["--port", "8766"] + args
        sys.argv = ["mcp"] + args
        swebench_main()
    else:
        print(f"Unknown server: {server}")
        print("Available: mbpp, swebench")
        sys.exit(1)


if __name__ == "__main__":
    main()
