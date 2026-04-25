# 🏏 IPL Insight MCP Agent

> **MCP Series — Episode 3 | Praveen Tech Lab**
> A production-style MCP server **+** AI agent that connects to live IPL 2026 cricket data via [CricAPI](https://cricapi.com).
> The agent pairs a FastMCP server with an OpenAI-powered client and a native Tkinter desktop UI.

📺 **Watch the full tutorial:** [MCP Server as a Bridge | Real API Integration in Python](https://youtu.be/IHA-ZalATeU)
💻 **Full series repo:** [mcp-from-zero-to-prod](https://github.com/praveentechlab/mcp-from-zero-to-prod)

---

## 📌 What This Is

This project demonstrates the **full MCP bridge pattern** — a real-world two-file agent:

```
┌─────────────────────────────────────────────────────────────────┐
│  ipl_agent.py  (MCP Client + OpenAI Tool Loop + Tkinter UI)     │
│                                                                  │
│  User Query  ──►  IPLAgent.chat()  ──►  OpenAI gpt-4o-mini      │
│                        │                      │                  │
│                        │◄── tool_calls ────────┘                 │
│                        │                                         │
│                        ▼  stdio transport                        │
│  ipl_mcp_server.py  (FastMCP Server + CricAPI REST calls)        │
│                                                                  │
│   Tool Result  ◄──  MCP Session  ◄──  CricAPI Response           │
└─────────────────────────────────────────────────────────────────┘
```

- **`ipl_mcp_server.py`** — FastMCP server; handles all REST calls, caching, and formatting. The client knows nothing about CricAPI or HTTP.
- **`ipl_agent.py`** — MCP client + OpenAI tool loop + desktop Tkinter UI. Launches the server as a subprocess over `stdio`, discovers tools automatically, and drives a multi-turn agentic loop.

---

## ✨ Features

### MCP Server (`ipl_mcp_server.py`)
- **4 live MCP tools** backed by real CricAPI data
- **Smart caching** — 5-minute TTL for live data, 24-hour TTL for series IDs
- **Auto-discovery** of IPL 2026 series ID — no hardcoded UUIDs
- **Disk-based series cache** — survives server restarts without burning API quota
- **Windows `stdout` fix** — stable `stdio` transport on Windows 11
- **Robust date parsing** — handles all CricAPI date formats
- **MCP Inspector compatible** — test every tool with zero client code

### AI Agent (`ipl_agent.py`)
- **`IPLAgent` class** — async MCP client + OpenAI `gpt-4o-mini` tool loop
- **Up to 6 tool turns** per query (`MAX_TOOL_TURNS = 6`)
- **Automatic tool chaining** — the LLM calls `get_ipl_recent` → extracts `match_id` → calls `get_ipl_scorecard` without user intervention
- **`on_tool_call` callback** — every tool invocation is surfaced to the UI in real time
- **`IPLApp` Tkinter UI** — full desktop GUI, no browser needed
  - 4 one-click quick-action buttons (Live Now, Recent Results, Scorecard, Player Search)
  - Scrollable response area with colour-coded tool-call annotations
  - Status bar with live agent state
  - Clear Output button
  - Resizable window (960 × 700 default, 800 × 560 minimum)
- **CLI smoke test** (`--cli` flag) — runs 3 test queries headlessly for CI / debugging

---

## 🛠️ MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_ipl_live_now` | Matches live right now (started, not ended) | None |
| `get_ipl_recent` | Recent completed results sorted by date | `count: int = 5` |
| `get_ipl_scorecard` | Full batting & bowling scorecard | `match_id: str` |
| `search_ipl_player` | Player profile, stats, career info | `player_name: str` |

> **Tool chaining:** The agent automatically calls `get_ipl_recent` first to obtain a `match_id`, then passes it to `get_ipl_scorecard`. No manual copy-paste needed.

---

## 📋 Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ (3.12 recommended) |
| pip / uv | Latest |
| CricAPI key | Free tier (100 req/day) |
| OpenAI API key | Any tier with `gpt-4o-mini` access |
| Tkinter | Bundled with CPython (no extra install on Windows/macOS) |
| Node.js | 18+ (for MCP Inspector only) |

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/praveentechlab/mcp-from-zero-to-prod.git
cd mcp-from-zero-to-prod/01-beginner/ipl_insight_mcp_agent
```

### 2. Create and activate a virtual environment

```bash
# Using uv (recommended)
uv venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Or standard Python
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

Copy the example env file and fill in your keys:

```bash
cp _env .env
```

Edit `.env`:

```env
CRICAPI_KEY="your-cricapi-key-here"
OPENAI_API_KEY="your-openai-key-here"
```

- Get your free CricAPI key at [cricapi.com](https://cricapi.com) — no credit card required, 100 req/day.
- Get your OpenAI key at [platform.openai.com](https://platform.openai.com).

### 5. Run the agent (desktop UI)

```bash
python ipl_agent.py
```

The Tkinter desktop app opens. Click any quick-action button or type a question.

### 6. CLI smoke test (no UI)

```bash
python ipl_agent.py --cli
```

Runs 3 preset queries headlessly and prints results to the terminal — useful for validating API keys and connectivity before opening the UI.

### 7. Test the server alone with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python ipl_mcp_server.py
```

Launches the server and opens Inspector in your browser. Call all four tools interactively without any client code.

---

## 🖥️ Desktop UI — Quick Reference

| Element | Description |
|---------|-------------|
| **Live Now** 🔴 | Fetches live match scores right now |
| **Recent Results** ✅ | Shows the last 5 completed match results |
| **Scorecard** 📋 | Full batting & bowling scorecard for the most recent match |
| **Player Search** 🏏 | Virat Kohli profile, stats, and career info |
| **Input box** | Type any free-form IPL 2026 question and press Enter or Send ➤ |
| **Clear Output** 🗑 | Wipes the response panel |
| **Status bar** | Shows agent state: Starting → Ready → Thinking… → Ready |
| **Tool annotations** | Yellow rows showing which MCP tool was called and with what arguments |

---

## 🧪 Testing Each Tool in MCP Inspector

| Step | Tool | Parameters | Expected Result |
|------|------|------------|-----------------|
| 1 | `get_ipl_live_now` | *(none)* | Live match scores or "no matches" fallback |
| 2 | `get_ipl_recent` | `count = 3` | 3 recent results with real Match UUIDs |
| 3 | `get_ipl_scorecard` | `match_id = <UUID from step 2>` | Full batting & bowling tables |
| 4 | `search_ipl_player` | `player_name = "Virat Kohli"` | Profile, stats, career info |

---

## 📂 Project Structure

```
ipl_insight_mcp_agent/
├── ipl_mcp_server.py       # FastMCP server — 4 tools, caching, series auto-discovery
├── ipl_agent.py            # MCP client + OpenAI tool loop + Tkinter desktop UI
├── requirements.txt        # Python dependencies
├── _env                    # Example env file (rename to .env)
├── .ipl_series_id.cache    # Auto-generated — disk cache for IPL series ID
└── README.md               # This file
```

---

## 🔧 Configuration

| Variable | Required | Used By | Description |
|----------|----------|---------|-------------|
| `CRICAPI_KEY` | ✅ Yes | Server + Agent | CricAPI authentication key |
| `OPENAI_API_KEY` | ✅ Yes | Agent only | OpenAI API key for `gpt-4o-mini` |

---

## 🏗️ Architecture Deep Dive

### Server: Windows `stdout` fix
The very first lines of `ipl_mcp_server.py` force UTF-8 encoding on `stdout` and `stdin`. This is **critical** — MCP uses `stdio` transport, and Windows default encoding silently breaks the connection if omitted.

### Server: Caching layer
Two TTL windows protect your free-tier API quota:

```python
_CACHE_TTL        = 300    # 5 minutes — match scores, player data
_SERIES_CACHE_TTL = 86400  # 24 hours  — series UUID (never changes mid-season)
```

The cache-aside pattern is applied consistently via `_get()`: cache hit → return instantly; cache miss → fetch, store, return.

### Server: Series auto-discovery
Rather than hardcoding the IPL 2026 series UUID, the server discovers it dynamically via a layered strategy:

1. Check in-memory cache
2. Check disk cache (`.ipl_series_id.cache`)
3. Try 4 search terms in order of specificity
4. Fall back to paginated series browse

Only **one API request** is ever made per process lifetime.

### Agent: MCP client lifecycle
`IPLAgent` manages the full async lifecycle:

```python
await agent.start()   # opens stdio transport, creates ClientSession, discovers tools
answer = await agent.chat("Who won the last IPL match?")
await agent.stop()    # closes all async contexts cleanly
```

The server is launched as a subprocess with `sys.executable -u ipl_mcp_server.py` and `PYTHONUNBUFFERED=1` — the same stdout fix applied from the client side.

### Agent: OpenAI tool loop
```
User query
    └─► LLM (gpt-4o-mini) with tools list
            └─► tool_calls returned
                    └─► MCP session.call_tool()
                            └─► tool result appended to messages
                                    └─► LLM again (up to 6 turns)
                                            └─► Final text response
```

Tool schemas are converted from MCP's `inputSchema` to OpenAI's function format via `_tool_to_openai()`.

### Agent: Thread model
The Tkinter UI runs on the main thread. `IPLAgent` is async — it runs on a dedicated `asyncio` event loop in a background thread. Queries are dispatched with `asyncio.run_coroutine_threadsafe()`, and UI updates are scheduled back with `self.after(0, ...)` — zero blocking of the GUI thread.

### Tool chaining (intentional design)
`get_ipl_scorecard` requires a `match_id` from `get_ipl_recent` or `get_ipl_live_now`. This is intentional — it teaches the LLM to chain tool calls, which is the foundation of agent reasoning. The system prompt enforces the correct routing order.

---

## 🔌 Connecting to Claude Desktop

Add to your Claude Desktop config:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ipl-insight-agent": {
      "command": "python",
      "args": ["C:/path/to/ipl_insight_mcp_agent/ipl_mcp_server.py"],
      "env": {
        "CRICAPI_KEY": "your-cricapi-key-here",
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

> Replace `C:/path/to/` with the actual absolute path on your machine. Only the **server** file is needed here — Claude Desktop is its own LLM host.

Once added, restart Claude Desktop and ask:
- *"Are there any live IPL 2026 matches right now?"*
- *"Show me the last 3 IPL match results with scorecards."*
- *"What are Rohit Sharma's career stats?"*

---

## 📦 Dependencies

```
mcp              # Model Context Protocol SDK (client + server)
python-dotenv    # .env file loading
openai           # OpenAI Async SDK (used by IPLAgent)
tkinter          # Desktop UI — bundled with CPython
```

> `urllib.request` and `json` are used for all HTTP calls in the server — no `requests` library needed, keeping dependencies minimal.

---

## ⚠️ Common Issues

**UI doesn't open / crashes immediately**
- Ensure both `OPENAI_API_KEY` and `CRICAPI_KEY` are set in `.env`
- Run `python ipl_agent.py --cli` first to rule out connectivity issues
- On Linux, install Tkinter: `sudo apt install python3-tk`

**"OPENAI_API_KEY is not set" error**
- The agent exits early if either key is missing. Check your `.env` file location — it must be in the same directory as `ipl_agent.py`

**Server doesn't start / Inspector shows no tools**
- Verify `CRICAPI_KEY` is in `.env`
- On Windows, confirm you're using Python from your virtual environment

**`No module named 'mcp'` or `No module named 'openai'`**
- Run `pip install -r requirements.txt` inside your activated virtual environment

**All tools return API errors**
- Check your CricAPI key at [cricapi.com](https://cricapi.com)
- Verify you haven't exceeded the 100 req/day free-tier limit
- The 5-minute cache means repeated calls within the window won't count against quota

**Series ID not found**
- IPL 2026 may not have started yet, or the series may be listed under a slightly different name on CricAPI
- Delete `.ipl_series_id.cache` to force a fresh lookup

**UI freezes while fetching**
- Expected — controls are disabled during a query. The status bar shows "Thinking…". Wait for the response to appear.

---

## 📺 MCP Series — Full Playlist

| Episode | Title | Link |
|---------|-------|------|
| Ep 01 | MCP Intro & Hello World | [Watch](https://youtu.be/v6ZU1psbLQk) |
| Ep 02 | Why Async Python Matters \| MCP Tools, Resources & Prompts | [Watch](https://youtu.be/-STdYXBmoIY) |
| **Ep 03** | **Real API Integration — MCP Server as a Bridge + AI Agent** | [**Watch**](https://youtu.be/IHA-ZalATeU) |
| Ep 04 | LLM Host + Full Agent Demo | Coming Soon |

---

## 🤝 Connect

| Platform | Link |
|----------|------|
| 🎥 YouTube | [Praveen Tech Lab](https://www.youtube.com/@PraveenTechLab) |
| 🔗 LinkedIn | [praveenkumar-basayyagari](https://linkedin.com/in/praveenkumar-basayyagari) |
| 💻 GitHub | [praveentechlab](https://github.com/praveentechlab/mcp-from-zero-to-prod) |

---

## 📄 License

MIT License — free to use, modify, and distribute. Attribution appreciated.

---

> Built with ❤️ by **Praveen Tech Lab** — No-fluff, hands-on GenAI & MCP tutorials.
