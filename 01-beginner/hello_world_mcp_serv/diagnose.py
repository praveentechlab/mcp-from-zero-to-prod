# File: diagnose.py
# Run: python diagnose.py

import sys
import os
import subprocess

print("=" * 50)
print("MCP DIAGNOSTIC TOOL")
print("=" * 50)

print(f"\n1. Python executable: {sys.executable}")
print(f"2. Python version:    {sys.version}")
print(f"3. Platform:          {sys.platform}")

print("\n4. Installed packages:")
try:
    import mcp
    print(f"   mcp:     ✅ {mcp.__version__}")
except Exception as e:
    print(f"   mcp:     ❌ {e}")

try:
    import anyio
    print(f"   anyio:   ✅ {anyio.__version__}")
except Exception as e:
    print(f"   anyio:   ❌ {e}")

try:
    import pydantic
    print(f"   pydantic:✅ {pydantic.__version__}")
except Exception as e:
    print(f"   pydantic:❌ {e}")

print("\n5. Testing server startup directly...")
result = subprocess.run(
    [sys.executable, "-u", "-c", """
import sys
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("test")

@mcp.tool()
def ping() -> str:
    return "pong"

print("SERVER_IMPORT_OK", flush=True)
"""],
    capture_output=True,
    text=True,
    timeout=10
)
print(f"   stdout: {result.stdout.strip()}")
print(f"   stderr: {result.stderr.strip()[:300]}")
print(f"   returncode: {result.returncode}")

if "SERVER_IMPORT_OK" in result.stdout:
    print("   ✅ Server imports work fine")
else:
    print("   ❌ Server fails to import — this is the root cause!")

print("\n6. Testing hello_server.py directly...")
result2 = subprocess.run(
    [sys.executable, "-u", "hello_server.py"],
    capture_output=True,
    text=True,
    timeout=5,
    input=""  # send empty stdin so it exits
)
print(f"   stdout: '{result2.stdout.strip()[:200]}'")
print(f"   stderr: '{result2.stderr.strip()[:300]}'")
print(f"   returncode: {result2.returncode}")