import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"
env["PYTHONIOENCODING"] = "utf-8"


server_params = StdioServerParameters(
    command=sys.executable,
    args=["-u", "movie_night_server.py"],
    env=env,
)

def heading(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def show_block(label: str, text: str) -> None:
    print(f"\n[{label}]")
    for line in text.strip().splitlines():
        print(f"  {line}")

async def demo_tools(session: ClientSession) -> None:
    heading("1. TOOLS DEMO")
    print("Tools do work. You call them with input arguments.")

    tools = await session.list_tools()
    print("\nAvailable tools:")
    for tool in tools.tools:
        print(f"  - {tool.name}: {tool.description}")
    
    response = await session.call_tool(
        "find_movies",
        {"query": "sci", "family_mode": True},
    )
    show_block("find_movies result", response.content[0].text)
    
    response = await session.call_tool(
        "suggest_snack",
        {"movie_title": "Inception"},
    )
    show_block("suggest_snack result", response.content[0].text)  
      

async def demo_resources(session: ClientSession) -> None:
    heading("2. RESOURCES DEMO")
    print("Resources are read-only data. You access them by URI.")

    resources = await session.list_resources()
    print("\nAvailable resources:")
    for resource in resources.resources:
        print(f"  - {resource.uri}: {resource.description}")
    
    response = await session.read_resource("movies://catalog")
    catalog = json.loads(response.contents[0].text)
    print(f"\nCatalog name : {catalog['collection']}")
    print(f"Total movies : {catalog['total_movies']}")
    print(f"Available    : {catalog['available_now']}")
    
    response = await session.read_resource("movies://family")
    family_movies = json.loads(response.contents[0].text)
    print("\nFamily movies:")
    for movie in family_movies:
        print(f"  - {movie['title']} ({movie['duration_min']} min)")
      

async def demo_prompts(session: ClientSession) -> None:
    heading("3. PROMPTS DEMO")
    print("Prompts are reusable AI instructions. They return message text for a model.")

    prompts = await session.list_prompts()
    print("\nAvailable prompts:")
    for prompt in prompts.prompts:
        print(f"  - {prompt.name}: {prompt.description}")
     
    response = await session.get_prompt(
        "movie_night_prompt",
        {"mood": "fun family sci-fi", "max_duration": "150"},
    )
    prompt_text = response.messages[0].content.text
    show_block("Generated prompt", prompt_text[:700] + "...")
    


async def main() -> None:
    heading("MCP MOVIE NIGHT DEMO")
    print("Starting demo_mcp_server.py through stdio...")
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected successfully.")
            #await demo_tools(session)
            #await demo_resources(session)
            await demo_prompts(session)


asyncio.run(main())       