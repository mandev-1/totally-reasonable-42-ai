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

        elif tool_name == "write_file":
            result = file_system.write_file(
                base_path,
                arguments["filepath"],
                arguments["content"],
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "delete_file":
            result = file_system.delete_file(
                base_path,
                arguments["filepath"],
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

        elif tool_name == "get_repo_tree":
            result = file_system.get_repo_tree(
                base_path,
                arguments.get("max_depth", 4),
                arguments.get("max_lines", 400),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "list_files":
            result = file_system.list_files(
                base_path,
                arguments.get("directory", "."),
                arguments.get("pattern", "*"),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "find_relevant":
            result = code_search.find_relevant(
                base_path,
                arguments["keywords"],
                arguments.get("max_files", 5),
                arguments.get("context_lines", 5),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name == "search_code":
            result = code_search.search_code(
                base_path,
                arguments["pattern"],
                arguments.get("file_pattern", "*.py"),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        elif tool_name in ("search_symbol", "search_function_or_class_definition_in_code"):
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

        elif tool_name == "validate_patch":
            r = execution.validate_patch(base_path, arguments.get("patch", ""))
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(r)}]}}

        elif tool_name in ("run_tests", "run_tests_with_failure_summary"):
            r = execution.run_tests(
                base_path,
                arguments["eval_script"],
                arguments.get("timeout", 1800),
                setup_script=arguments.get("setup_script"),
                test_command=arguments.get("test_command"),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(r)}]}}

        elif tool_name == "run_python_snippet":
            r = execution.run_python_snippet(
                base_path,
                arguments.get("code", ""),
                arguments.get("timeout", 60),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(r)}]}}

        elif tool_name == "run_root_cause_analysis":
            r = execution.run_root_cause_analysis(
                base_path,
                arguments.get("failure_summary", ""),
                arguments.get("output", ""),
                arguments.get("last_edit_file", ""),
            )
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(r)}]}}

        elif tool_name == "get_patch":
            result = execution.get_patch(base_path)
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": result}]}}

        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}}

    except Exception as e:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(e)}}


# SWE-bench optimized. recommended_workflow:
# root analysis -> list_files/search_code -> read/edit -> run_tests -> RCA-on-fail -> get_patch

TOOLS = [
    {
        "name": "get_repo_tree",
        "description": "UTILITY ONLY. Returns indented tree of the repository to understand structure. Prefer list_files/search_code first; use this only when targeted exploration is insufficient.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "max_depth": {"type": "integer", "default": 4},
                "max_lines": {"type": "integer", "default": 400},
            },
        },
    },
    {
        "name": "find_relevant",
        "description": "PRIMARY SEARCH TOOL for debugging tasks. Provide space-separated keywords from the problem (e.g. 'session headers Accept-Encoding'). Returns top matching files with surrounding context. Prefer this over multiple search_code calls when starting from a natural-language bug report.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "keywords": {"type": "string"},
                "max_files": {"type": "integer", "default": 5},
                "context_lines": {"type": "integer", "default": 5},
            },
            "required": ["keywords"],
        },
    },
    {
        "name": "search_symbol",
        "description": "Locate the definition of a function or class by name. Use after identifying a relevant symbol to jump directly to its implementation. Helps avoid scanning entire files manually.",
        "inputSchema": {
            "type": "object",
            "properties": {"base_path": {"type": "string"}, "name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "search_code",
        "description": "Regex-based search across files (output: /path/file.py:line_number line_content). Use when you know the exact symbol, string, or pattern to locate. Not ideal for vague natural-language queries — prefer find_relevant first.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "pattern": {"type": "string"},
                "file_pattern": {"type": "string", "default": "*.py"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "list_files",
        "description": "Primary structure tool. List files in a directory matching a glob pattern to quickly scope code/test locations before read_file.",
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
        "name": "find_references",
        "description": "Find all usages of a symbol in the repository. Requires a known definition location (filepath and line). Use to understand impact of modifying a function/class before editing.",
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
        "name": "read_file",
        "description": "Read file content with line numbers (<line_number>: <line_content>). Use only after narrowing down likely relevant files via list_files/find_relevant/search_code. Avoid reading large files entirely — prefer specifying start_line and end_line when possible.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "filepath": {"type": "string"},
                "start_line": {"type": "integer"},
                "end_line": {"type": "integer"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace an exact string in an existing file. old_str must match exactly (including whitespace). Always read the file first to confirm formatting before editing. Use for precise, minimal modifications to reduce patch size and regression risk.",
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
        "name": "write_file",
        "description": "Create or overwrite a file. Use primarily for creating new files. Prefer edit_file when modifying existing files to minimize unintended changes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "filepath": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["filepath", "content"],
        },
    },
    {
        "name": "delete_file",
        "description": "Delete a file if it exists. Use for temporary controller artifacts (e.g. ROOT.md) before finalizing.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "filepath": {"type": "string"},
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "validate_patch",
        "description": "Validate patch format before run_tests. Pass patch text from get_patch. Returns {valid, message}. Use to catch format errors early.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "patch": {"type": "string"},
            },
        },
    },
    {
        "name": "run_tests",
        "description": "Run the test suite using the provided evaluation script. Use after implementing a plausible fix. Do NOT use run_tests for print/debug introspection; use run_python_snippet instead. Returns structured JSON with success/message/output/patch and failure_summary on failures.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "eval_script": {"type": "string"},
                "timeout": {"type": "integer", "default": 1800},
            },
            "required": ["eval_script"],
        },
    },
    {
        "name": "run_python_snippet",
        "description": "Execute a short Python snippet in testbed env for cheap introspection (e.g., print expression args/assumptions). Use this instead of run_tests for debug prints.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "code": {"type": "string"},
                "timeout": {"type": "integer", "default": 60},
            },
            "required": ["code"],
        },
    },
    {
        "name": "run_root_cause_analysis",
        "description": "Analyze failed run_tests output. Returns root cause summary, failing tests, evidence lines, and code citations. Call immediately after run_tests failure.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_path": {"type": "string"},
                "failure_summary": {"type": "string"},
                "output": {"type": "string"},
                "last_edit_file": {"type": "string"},
            },
            "required": ["failure_summary"],
        },
    },
    {
        "name": "get_patch",
        "description": "Retrieve the unified git diff of all repository changes. Use to inspect and verify your modifications before running tests or finalizing a solution. Helps detect unintended edits.",
        "inputSchema": {
            "type": "object",
            "properties": {"base_path": {"type": "string"}},
        },
    },
]

RECOMMENDED_WORKFLOW = [
    "write_file",
    "edit_file",
    "list_files",
    "search_code",
    "find_relevant",
    "search_symbol",
    "read_file",
    "run_python_snippet",
    "run_tests",
    "run_root_cause_analysis",
    "get_patch",
    "get_repo_tree",
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
                "capabilities": {
                    "tools": {},
                    "recommended_workflow": RECOMMENDED_WORKFLOW,
                },
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


def run_http(port: int = 8766, host: str = "0.0.0.0"):
    """Run MCP server on HTTP. Use 0.0.0.0 to accept connections from Docker host."""
    server = HTTPServer((host, port), MCPHTTPHandler)
    print(f"SWE-tools MCP server running on http://{host}:{port}", file=sys.stderr)
    print(f"Set TESTBED_PATH for testbed root. Connect with: uv run sandbox --mcp-server http://localhost:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="SWE-tools MCP server")
    parser.add_argument("--port", type=int, default=8766, help="HTTP port (default: 8766)")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0 for Docker)")
    args = parser.parse_args()
    run_http(args.port, args.host)


if __name__ == "__main__":
    main()
