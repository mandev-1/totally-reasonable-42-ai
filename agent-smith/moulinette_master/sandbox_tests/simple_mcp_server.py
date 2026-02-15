#!/usr/bin/env python3
"""Simple MCP server for testing sandbox integration.

Supports both HTTP and stdio modes.

HTTP mode:
    python simple_mcp_server.py --http --port 8080

Stdio mode:
    python simple_mcp_server.py --stdio
"""
import argparse
import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler


# Simple tool implementations
def add_numbers(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

def multiply_numbers(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

def echo(message: str) -> str:
    """Echo a message back."""
    return f"Echo: {message}"

TOOLS = {
    "add": {
        "name": "add",
        "description": "Add two numbers",
        "parameters": {"a": "int", "b": "int"},
        "func": add_numbers,
    },
    "multiply": {
        "name": "multiply",
        "description": "Multiply two numbers",
        "parameters": {"a": "int", "b": "int"},
        "func": multiply_numbers,
    },
    "echo": {
        "name": "echo",
        "description": "Echo a message",
        "parameters": {"message": "str"},
        "func": echo,
    },
}


def handle_request(request: dict) -> dict:
    """Handle an MCP request."""
    method = request.get("method", "")
    params = request.get("params", {})
    request_id = request.get("id", 1)
    
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "test-mcp-server", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            }
        }
    
    elif method == "tools/list":
        tools_list = [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": {k: {"type": v} for k, v in tool["parameters"].items()},
                }
            }
            for tool in TOOLS.values()
        ]
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"tools": tools_list}
        }
    
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if tool_name not in TOOLS:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
            }
        
        try:
            result = TOOLS[tool_name]["func"](**arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": str(result)}]}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32000, "message": str(e)}
            }
    
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": f"Unknown method: {method}"}
        }


class MCPHTTPHandler(BaseHTTPRequestHandler):
    """HTTP handler for MCP requests."""
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request = json.loads(body)
            response = handle_request(request)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
        
        response_body = json.dumps(response).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response_body))
        self.end_headers()
        self.wfile.write(response_body)
    
    def log_message(self, format, *args):
        # Suppress request logging
        pass


def run_http_server(port: int):
    """Run the HTTP server."""
    server = HTTPServer(('localhost', port), MCPHTTPHandler)
    print(f"MCP HTTP server running on http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


def run_stdio_server():
    """Run the stdio server."""
    print("MCP stdio server running", file=sys.stderr)
    print("Waiting for JSON-RPC requests on stdin...", file=sys.stderr)
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            request = json.loads(line.strip())
            response = handle_request(request)
            
            print(json.dumps(response), flush=True)
            
        except json.JSONDecodeError as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {e}"}
            }
            print(json.dumps(error_response), flush=True)
        except KeyboardInterrupt:
            break


def main():
    parser = argparse.ArgumentParser(description="Simple MCP server for testing")
    parser.add_argument("--http", action="store_true", help="Run HTTP server")
    parser.add_argument("--stdio", action="store_true", help="Run stdio server")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (default: 8080)")
    
    args = parser.parse_args()
    
    if args.http:
        run_http_server(args.port)
    elif args.stdio:
        run_stdio_server()
    else:
        print("Specify --http or --stdio")
        sys.exit(1)


if __name__ == "__main__":
    main()
