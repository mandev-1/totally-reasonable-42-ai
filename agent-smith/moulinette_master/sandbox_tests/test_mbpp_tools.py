# Test: MBPP tools via MCP
# Run sandbox with: uv run sandbox --mcp-stdio "python mcp_tools_mbpp.py"
# Then cat this file into it

import json

# Test verify_code function (provided by MCP server)
code = """
def add(a, b):
    return a + b
"""

tests = [
    "assert add(1, 2) == 3",
    "assert add(0, 0) == 0",
    "assert add(-1, 1) == 0",
]

print("Testing verify_code tool via MCP...")

# verify_code is injected by the MCP server connection
# It returns a JSON string with success and output fields
result = verify_code(code=code, test_list=tests)
print(f"Result: {result}")

# Parse the result
try:
    parsed = json.loads(result)
    success = parsed.get("success", False)
    output = parsed.get("output", "")
    
    if success:
        print("\n=== MBPP TOOLS OK ===")
    else:
        print(f"Output: {output}")
        print("\n=== MBPP TOOLS FAILED ===")
except json.JSONDecodeError:
    # If not JSON, check for success indicators in raw result
    if "success" in result.lower() and "true" in result.lower():
        print("\n=== MBPP TOOLS OK ===")
    else:
        print("\n=== MBPP TOOLS FAILED ===")
