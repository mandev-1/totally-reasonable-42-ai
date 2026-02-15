#!/usr/bin/env python3
"""SWE-tools MCP server - file system, code search, and execution tools."""
import argparse
import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCP import file_system, code_search, execution


def get_base_path(arguments: dict) -> str:
    """Get testbed base path from args or env."""
    return arguments.get("base_path") or os.environ.get("TESTBED_PATH", "/testbed")


def handle_tools_call(params: dict, request_id: int) -> dict:
    """Dispatch tool call to appropriate module."""
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    base_path = get_base_path(arguments)

    try:
        if tool_name == "read_file":
            result = file_system.read_file(
                base_path,
                arguments["filepath"],
                arguments.get("start_line"),
                arguments.get("end_line"),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "edit_file":
            result = file_system.edit_file(
                base_path,
                arguments["filepath"],
                arguments["old_str"],
                arguments["new_str"],
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "list_files":
            result = file_system.list_files(
                base_path,
                arguments.get("directory", "."),
                arguments.get("pattern", "*"),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "search_code":
            result = code_search.search_code(
                base_path,
                arguments["pattern"],
                arguments.get("file_pattern", "*.py"),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "search_function_or_class_definition_in_code":
            result = code_search.search_function_or_class_definition_in_code(
                base_path,
                arguments["name"],
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "find_references":
            result = code_search.find_references(
                base_path,
                arguments["name"],
                arguments["filepath"],
                arguments["line"],
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "run_tests":
            r = execution.run_tests(
                base_path,
                arguments["eval_script"],
                arguments.get("timeout", 1800),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(r)}]}}

        elif tool_name == "get_patch":
            result = execution.get_patch(base_path)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

    except Exception as e:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(e)}}


TOOLS = [
    {
        "name": "read_file",
        "description": "Read file content with line numbers (cat -n format). Output: <line_number>: <line_content>",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string", "description": "Testbed root (default: TESTBED_PATH or /testbed)"},
                "filepath": {"type": "string", "description": "Path relative to base"},
                "start_line": {"type": "integer", "description": "First line (1-based)"},
                "end_line": {"type": "integer", "description": "Last line (1-based)"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace exact string in file",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "filepath": {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"},
            },
            "required": ["filepath", "old_str", "new_str"],
        },
    },
    {
        "name": "list_files",
        "description": "List files in directory matching pattern",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "directory": {"type": "string", "default": "."},
                "pattern": {"type": "string", "default": "*"},
            },
        },
    },
    {
        "name": "search_code",
        "description": "Grep-like search. Output: /path/file.py:line_number line_content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "pattern": {"type": "string", "description": "Regex pattern"},
                "file_pattern": {"type": "string", "default": "*.py"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "search_function_or_class_definition_in_code",
        "description": "Find definition of function or class",
        "inputSchema": {
            "type": "object",
            "properties": {"base_path": {"type": "string"}, "name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "find_references",
        "description": "Find all usages of a symbol",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "name": {"type": "string"},
                "filepath": {"type": "string"},
                "line": {"type": "integer"},
            },
            "required": ["name", "filepath", "line"],
        },
    },
    {
        "name": "run_tests",
        "description": "Execute the evaluation script in the testbed",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "eval_script": {"type": "string", "description": "Bash script to run tests"},
                "timeout": {"type": "integer", "default": 1800},
            },
            "required": ["eval_script"],
        },
    },
    {
        "name": "get_patch",
        "description": "Retrieve unified git diff of all changes in the repository",
        "inputSchema": {
            "type": "object",
            "properties": {"base_path": {"type": "string"}},
        },
    },
]


def handle_request(request: dict) -> dict:
    """Handle MCP JSON-RPC request."""
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", 1)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "swe-tools-mcp-server", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    elif method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}

    elif method == "tools/call":
        return handle_tools_call(params, request_id)

    else:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown method: {method}"}}


class MCPHTTPHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        try:
            request = json.loads(body)
            response = handle_request(request)
        except json.JSONDecodeError:
            response = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}

        response_body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(response_body))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        pass


def run_http(port: int = 8766):
    """Run MCP server on HTTP."""
    server = HTTPServer(("localhost", port), MCPHTTPHandler)
    print(f"SWE-tools MCP server running on http://localhost:{port}", file=sys.stderr)
    print(f"Set TESTBED_PATH for testbed root. Connect with: uv run sandbox --mcp-server http://localhost:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="SWE-tools MCP server")
    parser.add_argument("--port", type=int, default=8766, help="HTTP port (default: 8766)")
    args = parser.parse_args()
    run_http(args.port)


if __name__ == "__main__":
    main()
