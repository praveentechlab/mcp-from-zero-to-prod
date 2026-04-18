# 🏏 IPL Insight MCP Server

> **MCP Series — Episode 3 | Praveen Tech Lab**
> A production-style MCP server that connects an AI client to live IPL 2026 cricket data via the [CricAPI](https://cricapi.com) REST API.

📺 **Watch the full tutorial:** [MCP Server as a Bridge | Real API Integration in Python](https://youtu.be/IHA-ZalATeU)
💻 **Full series repo:** [mcp-from-zero-to-prod](https://github.com/praveentechlab/mcp-from-zero-to-prod)

---

## 📌 What This Is

This is a [FastMCP](https://github.com/jlowin/fastmcp) server that demonstrates **real API integration with MCP** — the bridge pattern where:

```
AI Client  →  Requests  →  MCP Server  →  API Calls  →  External Service (CricAPI)
           ←  Responses ←              ←  API Response ←
```

The MCP server acts as the **bridge** — the AI client sends natural language requests, and the server handles all the REST calls, JSON parsing, caching, and formatting. The client knows nothing about CricAPI or HTTP.

---

## ✨ Features

- **4 live MCP tools** backed by real CricAPI data
- **Smart caching** — 5-minute TTL for live data, 24-hour TTL for series IDs
- **Auto-discovery** of the IPL 2026 series ID — no hardcoded UUIDs
- **Disk-based series cache** — survives server restarts without burning API quota
- **Windows stdout fix** — ensures stable `stdio` transport on Windows 11
- **Robust date parsing** — handles all CricAPI date formats gracefully
- **MCP Inspector compatible** — test every tool without writing a client

---

## 🛠️ Tools Available

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_ipl_live_now` | Matches live right now (started, not ended) | None |
| `get_ipl_recent` | Recent completed results sorted by date | `count: int = 5` |
| `get_ipl_scorecard` | Full batting & bowling scorecard | `match_id: str` |
| `search_ipl_player` | Player profile, stats, career info | `player_name: str` |

> **Tool chaining:** Call `get_ipl_recent` → copy the Match ID → pass it to `get_ipl_scorecard`. Two tool calls, one coherent result.

---

## 📋 Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.10+ (3.12 recommended) |
| pip / uv | Latest |
| CricAPI key | Free tier (100 req/day) |
| Node.js | 18+ (for MCP Inspector only) |

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/praveentechlab/mcp-from-zero-to-prod.git
cd mcp-from-zero-to-prod/ep03-real-api-integration
```

### 2. Create and activate a virtual environment

```bash
# Using uv (recommended)
uv venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux

# Or using standard Python
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS / Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up your environment variables

Copy the example env file and fill in your API key:

```bash
cp _env .env
```

Edit `.env`:

```env
CRICAPI_KEY="your-cricapi-key-here"
```

Get your free API key at [cricapi.com](https://cricapi.com) — no credit card required, 100 requests/day.

### 5. Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python ipl_mcp_server.py
```

This launches your MCP server and opens the Inspector in your browser. You can call all four tools interactively — no client code needed.

---

## 🧪 Testing Each Tool in MCP Inspector

Once Inspector is open:

| Step | Tool | Parameters | Expected Result |
|------|------|------------|-----------------|
| 1 | `get_ipl_live_now` | *(none)* | Live match scores or "no matches" fallback |
| 2 | `get_ipl_recent` | `count = 3` | 3 recent results with real Match UUIDs |
| 3 | `get_ipl_scorecard` | `match_id = <UUID from step 2>` | Full batting & bowling tables |
| 4 | `search_ipl_player` | `player_name = "Virat Kohli"` | Profile, stats, career info |

---

## 📂 Project Structure

```
ep03-real-api-integration/
├── ipl_mcp_server.py       # Main MCP server — all tools defined here
├── requirements.txt        # Python dependencies
├── _env                    # Example env file (rename to .env)
├── .ipl_series_id.cache    # Auto-generated — disk cache for series ID
└── README.md               # This file
```

---

## 🔧 Configuration

All configuration is via environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `CRICAPI_KEY` | ✅ Yes | Your CricAPI authentication key |

---

## 🏗️ Architecture Deep Dive

### Windows stdout fix
The very first lines of `ipl_mcp_server.py` force UTF-8 encoding on `stdout` and `stdin`. This is **critical** — MCP uses `stdio` transport, and Windows default encoding silently breaks the connection if omitted.

### Caching layer
Two TTL windows protect your free-tier quota:

```python
_CACHE_TTL        = 300    # 5 minutes — match scores, player data
_SERIES_CACHE_TTL = 86400  # 24 hours  — series UUID (never changes mid-season)
```

The cache-aside pattern is applied consistently via `_get()`:
- Cache hit → return instantly, no API call
- Cache miss → fetch, store, return

### Series auto-discovery
Rather than hardcoding the IPL 2026 series UUID (which would break next year), the server discovers it dynamically via a layered search strategy:

1. Check in-memory cache
2. Check disk cache (`.ipl_series_id.cache`)
3. Try 4 search terms in order of specificity
4. Fall back to paginated series browse

Only **one API request** is ever made per process lifetime.

### Tool chaining
`get_ipl_scorecard` requires a `match_id` that comes from `get_ipl_recent` or `get_ipl_live_now`. This is intentional — it teaches the LLM to chain tool calls, which is the foundation of agent reasoning.

---

## 🔌 Connecting to Claude Desktop

Add this to your Claude Desktop config file:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ipl-insight-agent": {
      "command": "python",
      "args": ["C:/path/to/ep03-real-api-integration/ipl_mcp_server.py"],
      "env": {
        "CRICAPI_KEY": "your-cricapi-key-here",
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

> Replace `C:/path/to/` with the actual absolute path to the file on your machine.

Once added, restart Claude Desktop. You can then ask:
- *"Are there any live IPL matches right now?"*
- *"Show me the last 3 IPL match results"*
- *"What are Virat Kohli's career stats?"*

---

## 📦 Dependencies

```
mcp              # Model Context Protocol SDK
python-dotenv    # .env file loading
openai           # OpenAI SDK (used in Episode 4 host app)
```

> `urllib.request` and `json` are used for HTTP calls — no `requests` library needed, keeping dependencies minimal.

---

## ⚠️ Common Issues

**Server doesn't start / Inspector shows no tools**
- Ensure `CRICAPI_KEY` is set in your `.env` file
- Verify the `.env` file is in the same directory as `ipl_mcp_server.py`
- On Windows, make sure you're using the Python from your virtual environment

**`No module named 'mcp'` error**
- Run `pip install -r requirements.txt` inside your activated virtual environment

**All tools return API errors**
- Check your CricAPI key is valid at [cricapi.com](https://cricapi.com)
- Verify you haven't exceeded the 100 req/day free-tier limit
- The 5-minute cache means repeated calls within the window won't count toward quota

**Series ID not found**
- IPL 2026 may not have started yet, or the series may be listed under a slightly different name
- Check [cricapi.com](https://cricapi.com) directly for the current series listing

---

## 📺 MCP Series — Full Playlist

| Episode | Title | Link |
|---------|-------|------|
| Ep 01 | MCP Intro & Hello World | [Watch](https://youtu.be/v6ZU1psbLQk) |
| Ep 02 | Why Async Python Matters \| MCP Tools, Resources & Prompts | Coming Soon |
| **Ep 03** | **Real API Integration — MCP Server as a Bridge** | [**Watch**](https://youtu.be/IHA-ZalATeU) |
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
