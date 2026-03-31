# hello_client.py — REPLACE entire file with this

import asyncio
import sys
import os

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():

    # Build clean environment for Windows
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"

    server_params = StdioServerParameters(
        command=sys.executable,           # same Python as client
        args=["-u", "hello_server.py"],   # -u = unbuffered stdout
        env=env,
    )

    print("Connecting to server...")

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:

            await session.initialize()
            print("✅ Connected!\n")

            # List tools
            tools_resp = await session.list_tools()
            print(f"Tools found: {len(tools_resp.tools)}")
            for t in tools_resp.tools:
                #print(t)
                print(f"  • {t.name}: {t.description}")

            print()

            # Call say_hello
            r1 = await session.call_tool("say_hello", {"name": "Praveen"})
            print(f"👋 {r1.content[0].text}")

            # Call add_numbers
            r2 = await session.call_tool("add_numbers", {"a": 15, "b": 25})
            print(f"🔢 {r2.content[0].text}")

asyncio.run(main())