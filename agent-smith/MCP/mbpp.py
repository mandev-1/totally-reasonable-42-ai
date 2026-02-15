#!/usr/bin/env python3
"""MBPP MCP server - provides run_tests tool for executing code in Docker."""
import argparse
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

# Add project root for imports
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCP.run_tests import run_code_in_docker


def run_tests(code: str, test_imports: list[str], test_list: list[str], timeout: float = 30.0) -> dict:
    """
    Run solution code with tests in Docker.

    Args:
        code: The solution function code.
        test_imports: List of import lines.
        test_list: List of assert statements.
        timeout: Execution timeout in seconds.

    Returns:
        dict with success (bool), output (str), message (str).
    """
    full_code = code + "\n"
    if test_imports:
        full_code += "\n".join(test_imports) + "\n"
    if test_list:
        full_code += "\n".join(test_list) + "\n"

    success, output = run_code_in_docker(full_code, timeout=timeout)
    return {
        "success": success,
        "output": output,
        "message": "All tests passed!" if success else "Tests failed",
    }


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
                "serverInfo": {"name": "mbpp-mcp-server", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "run_tests",
                        "description": "Execute solution code with tests in Docker. Returns success status and output.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string", "description": "The solution function code"},
                                "test_imports": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Import lines for tests",
                                    "default": [],
                                },
                                "test_list": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "Assert statements for tests",
                                    "default": [],
                                },
                                "timeout": {
                                    "type": "number",
                                    "description": "Execution timeout in seconds",
                                    "default": 30,
                                },
                            },
                            "required": ["code"],
                        },
                    }
                ]
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name != "run_tests":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
            }

        try:
            code = arguments.get("code", "")
            test_imports = arguments.get("test_imports", [])
            test_list = arguments.get("test_list", [])
            timeout = arguments.get("timeout", 30.0)

            result = run_tests(code, test_imports, test_list, timeout)
            text = json.dumps(result)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": text}]},
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(e)},
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"},
        }


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


def run_http(port: int = 8765):
    """Run MCP server on HTTP."""
    server = HTTPServer(("localhost", port), MCPHTTPHandler)
    print(f"MBPP MCP server running on http://localhost:{port}", file=sys.stderr)
    print(f"Connect with: uv run sandbox --mcp-server http://localhost:{port}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        server.shutdown()


def main():
    parser = argparse.ArgumentParser(description="MBPP MCP server")
    parser.add_argument("--port", type=int, default=8765, help="HTTP port (default: 8765)")
    args = parser.parse_args()
    run_http(args.port)


if __name__ == "__main__":
    main()
