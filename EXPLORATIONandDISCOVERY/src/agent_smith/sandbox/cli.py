"""Sandbox CLI (Section 4.2)."""

import argparse
import json
import sys
from pathlib import Path

from agent_smith.models.sandbox import SandboxConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent Smith sandbox")
    parser.add_argument(
        "config",
        nargs="?",
        default=None,
        help="Path to sandbox JSON config (e.g. sandbox_template.json)",
    )
    parser.add_argument("--mcp-server", help="MCP server URL")
    parser.add_argument(
        "--mcp-stdio",
        help='MCP stdio command, e.g. "python mcp_tools_mbpp.py"',
    )
    args = parser.parse_args()

    if args.config:
        path = Path(args.config)
        if path.exists():
            config = SandboxConfig.model_validate(json.loads(path.read_text()))
        else:
            print(f"Config file not found: {path}", file=sys.stderr)
            sys.exit(1)
    else:
        config = SandboxConfig()

    print("Sandbox config loaded.")
    print(f"  authorized_imports: {len(config.authorized_imports)} modules")
    print(f"  allowed_directories: {config.allowed_directories}")
    print(f"  max_execution_time_seconds: {config.max_execution_time_seconds}")
    print(f"  max_memory_mb: {config.max_memory_mb}")
    if args.mcp_server:
        print(f"  MCP server: {args.mcp_server}")
    if args.mcp_stdio:
        print(f"  MCP stdio: {args.mcp_stdio}")

    print("\nInteractive sandbox (placeholder). Run with MCP tools for full functionality.")


if __name__ == "__main__":
    main()
