"""Sandbox CLI - loads config and runs in Docker. Supports MCP integration."""

import argparse
import json
import sys
from pathlib import Path


def load_config(config_path: str | None = None) -> dict:
    """Load sandbox config from JSON or return defaults."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        "authorized_imports": [
            "math", "math.*", "collections", "collections.*",
            "itertools", "re", "json", "typing", "typing.*",
            "functools", "operator", "heapq", "bisect", "copy",
            "string", "random", "datetime", "datetime.*",
            "array", "cmath",
        ],
        "allowed_directories": ["/testbed", "/tmp/agent"],
        "max_execution_time_seconds": 30,
        "max_memory_mb": 512,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Sandbox with optional MCP")
    parser.add_argument("config", nargs="?", help="Config JSON path")
    parser.add_argument("--mcp-server", help="MCP server URL (e.g. http://localhost:8765)")
    parser.add_argument("--mcp-stdio", help="MCP stdio command (e.g. python MCP/mbpp.py)")
    args, _ = parser.parse_known_args()

    config_path = args.config
    config = load_config(config_path)
    imports = config.get("authorized_imports", [])
    dirs = config.get("allowed_directories", [])
    max_time = config.get("max_execution_time_seconds", 30)
    max_mem = config.get("max_memory_mb", 512)

    print("Sandbox config loaded.")
    print(f"  authorized_imports: {len(imports)} modules")
    print(f"  allowed_directories: {dirs}")
    print(f"  max_execution_time_seconds: {max_time}")
    print(f"  max_memory_mb: {max_mem}")
    print()
    if args.mcp_server:
        print(f"MCP server: {args.mcp_server}")
    elif args.mcp_stdio:
        print(f"MCP stdio: {args.mcp_stdio}")
    print("Interactive sandbox. Run with MCP for agent tools.")


if __name__ == "__main__":
    main()
