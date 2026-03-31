# 🤖 MCP Hello World — Windows Setup Guide & Tools

![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![MCP](https://img.shields.io/badge/MCP-CLI-green)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![Status](https://img.shields.io/badge/Status-Working-brightgreen)

> A beginner-friendly MCP (Model Context Protocol) Hello World project
> with complete setup, code explanation, and Windows troubleshooting guide.

---

## 📁 Project Structure

```
Hello_world_MCP_Serv/
└── hello_world/
    ├── .venv/                        # Virtual environment
    ├── docs/                         # Documentation folder
    │   └── MCP_Windows_Fix_Guide.docx  # Bug fix guide (Word document)
    ├── hello_server.py               # MCP Server — exposes tools
    ├── hello_client.py               # MCP Client — calls tools
    ├── diagnose.py                   # Diagnostic script for troubleshooting
    └── README.md                     # This file
```

---

## 📋 Prerequisites

| Requirement | Version | Check Command |
|---|---|---|
| Python | 3.11 or higher | `python --version` |
| pip | Latest | `pip --version` |
| uv (optional) | Any | `uv --version` |

---

## ⚙️ Installation

### Step 1 — Clone or Create Project Folder

```powershell
mkdir Hello_world_MCP_Serv
cd Hello_world_MCP_Serv
mkdir hello_world
cd hello_world
```

### Step 2 — Create Virtual Environment

```powershell
# Create venv
python -m venv .venv

# Activate venv (Windows PowerShell)
.venv\Scripts\activate

# You should see (.venv) prefix in your terminal:
# (.venv) PS C:\...\hello_world>
```

### Step 3 — Install MCP

```powershell
pip install "mcp[cli]"
```

### Step 4 — Verify Installation

```powershell
python -c "from mcp.server.fastmcp import FastMCP; print('MCP installed OK')"
```

---

## 📄 Server Code — hello_server.py

```python
# hello_server.py

import sys

# Windows fix — MUST be first lines before any other import
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("hello_world")

@mcp.tool()
def say_hello(name: str) -> str:
    """Say hello to someone by name."""
    return f"Hello, {name}! MCP is working on Windows!"

@mcp.tool()
def add_numbers(a: int, b: int) -> str:
    """Add two numbers together."""
    return f"{a} + {b} = {a + b}"

@mcp.tool()
def get_platform() -> str:
    """Get current platform info."""
    import platform
    return f"Running on: {platform.system()} {platform.release()}"

if __name__ == "__main__":
    mcp.run()
```

---

## 📄 Client Code — hello_client.py

```python
# hello_client.py

import asyncio
import sys
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():

    # Windows-safe environment settings
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"       # Disable output buffering
    env["PYTHONIOENCODING"] = "utf-8"   # Fix encoding on Windows

    # Configure how to launch the server
    server_params = StdioServerParameters(
        command=sys.executable,           # Use same Python as client
        args=["-u", "hello_server.py"],   # -u = unbuffered mode
        env=env,
    )

    print("Connecting to MCP server...")

    # Layer 1 — Transport: spawns server and opens read/write pipes
    async with stdio_client(server_params) as (read, write):

        # Layer 2 — Protocol: wraps pipes in MCP JSON-RPC session
        async with ClientSession(read, write) as session:

            # Handshake with server
            await session.initialize()
            print("✅ Connected!\n")

            # List all available tools
            tools_resp = await session.list_tools()
            print(f"🔧 Tools found: {len(tools_resp.tools)}")
            for t in tools_resp.tools:
                print(f"   • {t.name}: {t.description}")
            print()

            # Call tool: say_hello
            r1 = await session.call_tool("say_hello", {"name": "Praveen"})
            print(f"👋 {r1.content[0].text}")

            # Call tool: add_numbers
            r2 = await session.call_tool("add_numbers", {"a": 15, "b": 25})
            print(f"🔢 {r2.content[0].text}")

            # Call tool: get_platform
            r3 = await session.call_tool("get_platform", {})
            print(f"💻 {r3.content[0].text}")

asyncio.run(main())
```

---

## 🧠 Code Explanation — Key Lines

### The Two Core Lines Explained

```python
async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
```

These two lines work in **two layers**:

---

#### Layer 1 — `stdio_client(server_params)` — The Transport Layer

```
What it does:
  Spawns hello_server.py as a child subprocess
  Opens two async pipe streams:
    read  → incoming data  (server → client)
    write → outgoing data  (client → server)

Visual:
  hello_client.py            hello_server.py
  ───────────────            ───────────────
                  ──write──▶
    (your code)                 (MCP server)
                  ◀──read───
```

| Part | Meaning |
|---|---|
| `async with` | Opens async context — auto-cleans up when done |
| `stdio_client(server_params)` | Launches server process, creates pipes |
| `as (read, write)` | Unpacks streams — read = from server, write = to server |

**When the block exits** → server process is automatically terminated, pipes closed.

---

#### Layer 2 — `ClientSession(read, write)` — The Protocol Layer

```
What it does:
  Wraps the raw pipes in MCP JSON-RPC protocol
  Gives you clean Python methods instead of raw bytes

Without ClientSession (raw pipes):             With ClientSession:
  raw = '{"jsonrpc":"2.0","method":...}'         result = await session.call_tool(
  await write.send(raw.encode())                     "say_hello", {"name": "Praveen"}
  response = await read.receive()                )
  # parse bytes manually...                      print(result.content[0].text)
```

| Method | What It Does |
|---|---|
| `session.initialize()` | Handshake with server — must call first |
| `session.list_tools()` | Get all tools the server exposes |
| `session.call_tool(name, args)` | Invoke a specific tool |
| `session.list_resources()` | Get available resources |
| `session.list_prompts()` | Get available prompts |

---

#### Full Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    hello_client.py                       │
│                                                          │
│  stdio_client(server_params)  ← LAYER 1: Transport      │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Spawns hello_server.py subprocess                 │  │
│  │  read  ◀──────────────────  server stdout         │  │
│  │  write ─────────────────▶   server stdin          │  │
│  │                                                    │  │
│  │  ClientSession(read, write)  ← LAYER 2: Protocol  │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  Handles MCP JSON-RPC encoding               │  │  │
│  │  │  session.initialize()   → handshake          │  │  │
│  │  │  session.list_tools()   → discover tools     │  │  │
│  │  │  session.call_tool()    → invoke tool        │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

> **Simple Analogy:**
> `stdio_client()` dials the phone call and establishes the connection.
> `ClientSession()` is the language/protocol you speak on that call.
> `session.call_tool()` is the actual conversation.

---

## ▶️ How to Run

### Step 1 — Activate Virtual Environment

```powershell
cd C:\Users\prave\OneDrive\Desktop\Praveen\Prac\MCP_Prac\Hello_world_MCP_Serv\hello_world
.venv\Scripts\activate
```

### Step 2 — Test Server Alone First (Always Do This)

```powershell
python hello_server.py
```

**Expected:** Terminal hangs silently — this means the server started correctly
and is waiting for input. Press `Ctrl+C` to stop.

```
# ✅ Good — server waits silently
# ❌ Bad  — if it shows an error and exits, fix server first
```

### Step 3 — Run the Client

```powershell
python hello_client.py
```

---

## ✅ Expected Output

```
Connecting to MCP server...
✅ Connected!

🔧 Tools found: 3
   • say_hello: Say hello to someone by name.
   • add_numbers: Add two numbers together.
   • get_platform: Get current platform info.

👋 Hello, Praveen! MCP is working on Windows!
🔢 15 + 25 = 40
💻 Running on: Windows 11
```

---

## 🔍 Test with MCP Inspector (No Client Code Needed)

MCP provides a built-in browser UI to test your server tools directly.

```powershell
# Run the MCP inspector
mcp dev hello_server.py
```
![1](https://github.com/user-attachments/assets/22e7ce6d-dc38-4c70-aa0b-d1fdfad1b503)

- Opens browser at **http://localhost:6274**
- Lists all tools visually
- Call tools with custom parameters
- See raw JSON request/response
- Great for debugging server tools before writing client code

---
![2](https://github.com/user-attachments/assets/b0b89d11-55eb-44d9-a58b-9372fc617d20)

![3](https://github.com/user-attachments/assets/5ddaaf75-334f-4fe7-b76b-cccba5cf7e5f)

![4](https://github.com/user-attachments/assets/65c399ac-1a37-457a-b183-e0e8d50ed9ec)

![5](https://github.com/user-attachments/assets/dfdf15e4-e725-4138-8f85-cbe68d944a97)


## 🚨 Troubleshooting Guide

### Error: `McpError: Connection closed`

This is the most common Windows error. It means the server process
crashed before the client could connect.

#### Quick Fix Checklist

```
Step 1  →  Run server alone:  python hello_server.py
           Does it hang silently? → Server is OK, go to Step 2
           Does it crash?         → Fix server code first

Step 2  →  Make sure venv is activated
           .venv\Scripts\activate

Step 3  →  Confirm you are using sys.executable in client
           command=sys.executable  (not command="python")

Step 4  →  Confirm -u flag is in server args
           args=["-u", "hello_server.py"]

Step 5  →  Confirm env dict has PYTHONUNBUFFERED=1

Step 6  →  Set env variables manually in PowerShell:
           $env:PYTHONUNBUFFERED = "1"
           $env:PYTHONIOENCODING = "utf-8"
           python hello_client.py
```

---

### Common Errors & Fixes

| Error | Cause | Fix |
|---|---|---|
| `McpError: Connection closed` | Windows stdout buffering | Add `-u` flag + `sys.executable` |
| `ModuleNotFoundError: mcp` | venv not activated | Run `.venv\Scripts\activate` |
| `python not found` | Python not in PATH | Use full path or reinstall Python |
| `UnicodeEncodeError` | Windows encoding issue | Add `PYTHONIOENCODING=utf-8` to env |
| `Connection refused` | Wrong port / server not running | Start server first in HTTP mode |
| `ExceptionGroup: unhandled errors` | Server crash on startup | Test server alone first |

---

### Run the Diagnostic Script

Save this as `diagnose.py` and run it to see exactly what is failing:

```python
# diagnose.py
import sys, os, subprocess

print("=" * 50)
print("MCP DIAGNOSTIC TOOL")
print("=" * 50)
print(f"\nPython executable : {sys.executable}")
print(f"Python version    : {sys.version}")
print(f"Platform          : {sys.platform}")

try:
    import mcp
    print(f"MCP version       : {mcp.__version__} ✅")
except Exception as e:
    print(f"MCP import        : FAILED ❌ — {e}")

print("\nTesting server startup...")
result = subprocess.run(
    [sys.executable, "-u", "hello_server.py"],
    capture_output=True, text=True, timeout=5, input=""
)
print(f"stdout   : {result.stdout[:200]!r}")
print(f"stderr   : {result.stderr[:300]!r}")
print(f"exitcode : {result.returncode}")
```

```powershell
python diagnose.py
```

---

### Reinstall MCP (Nuclear Option)

Use this if nothing else works:

```powershell
# 1. Deactivate venv
deactivate

# 2. Delete old venv
Remove-Item -Recurse -Force .venv

# 3. Create fresh venv
python -m venv .venv

# 4. Activate
.venv\Scripts\activate

# 5. Install MCP fresh
pip install "mcp[cli]"

# 6. Verify
python -c "from mcp.server.fastmcp import FastMCP; print('OK ✅')"

# 7. Run again
python hello_server.py   # test server alone first
python hello_client.py
```

---

## 📂 Bug Fix Documentation

A detailed Word document covering the complete diagnosis and all fixes
is included in the `docs/` folder of this project.

### Setting Up the docs/ Folder

```powershell
# Create docs directory inside your project
mkdir docs
```

### Copy the Fix Guide into docs/

```powershell
# If you downloaded MCP_Windows_Fix_Guide.docx, move it here:
copy MCP_Windows_Fix_Guide.docx docs\

# Or from Downloads folder:
copy C:\Users\prave\Downloads\MCP_Windows_Fix_Guide.docx docs\
```

### docs/ Folder Structure

```
docs/
└── MCP_Windows_Fix_Guide.docx    # Complete Windows bug fix guide
```

### What the Fix Guide Contains

| Section | Content |
|---|---|
| Section 1 | Error overview, environment details, root cause analysis |
| Section 2 | Diagnosis steps — server test, diagnostic script, path checks |
| Section 3 | Four fixes in priority order with full code examples |
| Section 4 | Complete working server + client code (copy-paste ready) |
| Section 5 | Fix summary table and step-by-step checklist |
| Section 6 | MCP Inspector browser tool usage |

> Open the `.docx` file with **Microsoft Word** or **LibreOffice Writer**

---

## 📦 Dependencies

```
mcp[cli] >= 1.6.0     # Core MCP library
pydantic >= 2.0.0     # Input validation (installed with mcp)
anyio                 # Async I/O (installed with mcp)
httpx                 # HTTP client (installed with mcp)
```

Install all at once:

```powershell
pip install "mcp[cli]"
```

---

## 💡 Key Concepts

| Term | Meaning |
|---|---|
| **MCP Server** | Python script that exposes tools the AI can call |
| **MCP Client** | Python script that connects to server and calls tools |
| **Tool** | A function decorated with `@mcp.tool()` that AI can invoke |
| **stdio transport** | Communication via stdin/stdout pipes (default) |
| **HTTP transport** | Communication via HTTP on a port (use `--http` flag) |
| **`async with`** | Context manager that auto-closes resources when done |
| **`ClientSession`** | High-level MCP protocol handler — gives clean Python API |
| **`stdio_client`** | Transport layer — spawns server and manages pipes |

---

## 🗺️ What to Learn Next

```
✅ Hello World Server + Client    ← You are here
⬜ Multiple Tools + Validation
⬜ HTTP Transport Mode
⬜ MCP Resources
⬜ MCP Prompts
⬜ Real API Integration
⬜ SQLite Database Server
⬜ AI Agent Loop (with Claude)
⬜ Multi-Server Agent
⬜ Production Patterns
```

---

## 📝 Notes

- Always **activate your venv** before running any scripts
- Always **test the server alone** before running the client
- On Windows, always use **`sys.executable`** instead of `"python"` in `StdioServerParameters`
- The **`-u` flag** is critical on Windows — it disables stdout buffering
- Use **`mcp dev hello_server.py`** to test tools visually in the browser

---

*MCP Hello World Guide — March 2026*
