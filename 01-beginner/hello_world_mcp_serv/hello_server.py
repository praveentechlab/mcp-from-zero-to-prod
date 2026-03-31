# hello_server.py — REPLACE entire file with this

import sys

# Windows fix — must be FIRST lines before any other import
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("hello_world")

@mcp.tool()
def say_hello(name: str) -> str:
    """Say hello to someone."""
    return f"Hello, {name}! MCP is working!"

@mcp.tool()
def add_numbers(a: int, b: int) -> str:
    """Add two numbers together."""
    return f"{a} + {b} = {a + b}"

if __name__ == "__main__":
    mcp.run()