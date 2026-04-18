"""
IPL Insight MCP Server
======================
FastMCP server with 4 tools backed by cricapi.com free API.
Series ID auto-discovered at runtime — no hardcoding.

Tools:
  get_ipl_live_now    — live match scores
  get_ipl_recent      — recent completed results
  get_ipl_scorecard   — full batting/bowling scorecard
  search_ipl_player   — player profile & stats
"""

# ── Windows stdout fix — MUST be first, before ALL other imports ────────────
import sys
import io as _io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = _io.TextIOWrapper(
        sys.stdout.buffer,
        encoding="utf-8",
        errors="replace",
        line_buffering=False,
        write_through=True,
    )
if hasattr(sys.stdin, "buffer"):
    sys.stdin = _io.TextIOWrapper(
        sys.stdin.buffer,
        encoding="utf-8",
        errors="replace",
    )
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True, encoding="utf-8")

# ── All other imports come AFTER the stdout fix ───────────────────────────────
import os, json, time, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
load_dotenv()
from mcp.server.fastmcp import FastMCP

# ── Config ────────────────────────────────────────────────────────────────────
API_KEY  = os.getenv("CRICAPI_KEY", "")
BASE_URL = "https://api.cricapi.com/v1"

mcp = FastMCP("IPL-Insight-Agent")

# Disk-based series ID cache so restarts don't re-burn API quota
_SERIES_ID_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".ipl_series_id.cache")

# ── Cache ─────────────────────────────────────────────────────────────────────
_cache: dict = {}
_CACHE_TTL        = 300   # 5 min — reduces API calls significantly
_SERIES_CACHE_TTL = 86400 # 24 hours — series ID never changes mid-season

def _raw_get(endpoint: str, params: dict | None = None) -> dict:
    p = {"apikey": API_KEY}
    if params:
        p.update(params)
    url = f"{BASE_URL}/{endpoint}?{urllib.parse.urlencode(p)}"
    req = urllib.request.Request(url, headers={"User-Agent": "IPL-MCP/2.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    if isinstance(data, dict) and data.get("status") == "failure":
        raise RuntimeError(data.get("reason", "API request failed"))
    return data

def _get(endpoint: str, params: dict | None = None, ttl: int = _CACHE_TTL) -> dict:
    key = endpoint + json.dumps(params or {}, sort_keys=True)
    now = time.time()
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    data = _raw_get(endpoint, params)
    _cache[key] = {"ts": now, "data": data}
    return data

# ── Date helpers ──────────────────────────────────────────────────────────────

def _parse_dt(date_str: str) -> datetime | None:
    """
    Parse cricapi date strings robustly.
    Handles: "2026-04-20T14:00:00"  "2026-04-20T14:00:00Z"
             "2026-04-20T14:00:00+00:00"  "2026-04-20"  "20 Apr 2026"
    Returns UTC-aware datetime or None.
    """
    if not date_str:
        return None
    s = date_str.strip()

    # ISO variants
    for fmt_s in (s, s.replace("Z", "+00:00")):
        try:
            dt = datetime.fromisoformat(fmt_s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    # Date-only: "2026-04-20"
    try:
        dt = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        pass

    # Human: "20 Apr 2026"
    for fmt in ("%d %b %Y", "%d %B %Y"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            pass

    return None

def _fmt_dt(dt: datetime | None, fallback: str = "TBA") -> str:
    if dt is None:
        return fallback
    return dt.strftime("%d %b %Y  %H:%M UTC")

def _fmt_score(scores: list) -> str:
    if not scores:
        return "Score N/A"
    return "  |  ".join(
        f"{s.get('inning','')}: {s.get('r',0)}/{s.get('w',0)} ({s.get('o',0)} ov)"
        for s in scores
    )

# ── Series auto-discovery ─────────────────────────────────────────────────────
_ipl_series_id: str | None = None

def _find_ipl_series_id() -> str | None:
    """
    Returns the IPL 2026 series ID.
    Priority: in-memory → disk cache → single API call.
    Only ever makes ONE API request per process lifetime to avoid rate-limiting.
    """
    global _ipl_series_id
    if _ipl_series_id:
        return _ipl_series_id

    # Check disk cache (persists across restarts)
    try:
        if os.path.exists(_SERIES_ID_FILE):
            with open(_SERIES_ID_FILE) as f:
                cached = json.load(f)
            age = time.time() - cached.get("ts", 0)
            if age < _SERIES_CACHE_TTL and cached.get("id"):
                _ipl_series_id = cached["id"]
                return _ipl_series_id
    except Exception:
        pass

    # Try multiple search terms
    search_terms = ["Indian Premier League 2026", "Indian Premier League", "IPL 2026", "IPL"]
    for term in search_terms:
        try:
            data = _get("series", {"search": term, "offset": 0}, ttl=_SERIES_CACHE_TTL)
            for s in data.get("data", []):
                name = s.get("name", "").lower()
                is_ipl  = "ipl" in name or "indian premier" in name
                is_2026 = "2026" in name
                if is_ipl and is_2026:
                    _ipl_series_id = s["id"]
                    try:
                        with open(_SERIES_ID_FILE, "w") as f:
                            json.dump({"id": _ipl_series_id, "ts": time.time()}, f)
                    except Exception:
                        pass
                    return _ipl_series_id
        except Exception as e:
            print(f"[series-search] term={term!r} error={e}", file=sys.stderr)
            continue

    # Last resort: page through /series with no query
    try:
        for offset in (0, 25, 50):
            data = _get("series", {"offset": offset}, ttl=_SERIES_CACHE_TTL)
            for s in data.get("data", []):
                name = s.get("name", "").lower()
                if ("ipl" in name or "indian premier" in name) and "2026" in name:
                    _ipl_series_id = s["id"]
                    try:
                        with open(_SERIES_ID_FILE, "w") as f:
                            json.dump({"id": _ipl_series_id, "ts": time.time()}, f)
                    except Exception:
                        pass
                    return _ipl_series_id
    except Exception as e:
        raise RuntimeError(f"Series lookup failed (paginated fallback): {e}")

    return None

def _series_matches() -> list[dict]:
    sid = _find_ipl_series_id()
    if not sid:
        return []
    data = _get("series_info", {"id": sid}, ttl=_SERIES_CACHE_TTL)
    return data.get("data", {}).get("matchList", [])

def _current_ipl_matches() -> list[dict]:
    sid = _find_ipl_series_id()
    data = _get("currentMatches", {"offset": 0})
    all_m = data.get("data", [])
    if sid:
        ipl = [m for m in all_m if sid in m.get("series_id", "")]
        if ipl:
            return ipl
    return [m for m in all_m
            if "ipl" in m.get("name","").lower()
            or "indian premier" in m.get("name","").lower()]


# ════════════════════════════════════════════════════════════════════
# TOOLS  (only 4 retained)
# ════════════════════════════════════════════════════════════════════

@mcp.tool()
def get_ipl_live_now() -> str:
    """
    Get IPL 2026 matches that are ACTUALLY live right now.
    Shows current score, overs, live status, and Match ID.
    """
    try:
        sid = _find_ipl_series_id()
        if not sid:
            return "⚠️  Could not locate IPL 2026 series."

        matches = _current_ipl_matches()
        live = [m for m in matches
                if m.get("matchStarted", False) and not m.get("matchEnded", False)]

        if not live:
            return (
                "🏏 No IPL 2026 matches live right now.\n"
                f"   Series ID : {sid}\n"
                "   Use get_ipl_recent() to see the latest completed results."
            )

        lines = [f"🔴 LIVE IPL 2026  [{len(live)} match(es)]\n" + "═" * 46]
        for m in live:
            lines.append(
                f"\n📍 {m.get('name','')}\n"
                f"   Match ID : {m.get('id','N/A')}\n"
                f"   Score    : {_fmt_score(m.get('score',[]))}\n"
                f"   Status   : {m.get('status','')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def get_ipl_recent(count: int = 5) -> str:
    """
    Get the most recent IPL 2026 completed match results with Match IDs.

    Args:
        count: Number of results (default 5, max 10).
    """
    count = min(max(1, count), 10)
    try:
        sid = _find_ipl_series_id()
        if not sid:
            return "⚠️  Could not locate IPL 2026 series."

        # Try currentMatches first (has live scores)
        completed = [m for m in _current_ipl_matches() if m.get("matchEnded", False)]

        # Fallback to series matchList
        if not completed:
            completed = [m for m in _series_matches() if m.get("matchEnded", False)]

        if not completed:
            return "No completed IPL 2026 matches found yet."

        def _key(m):
            dt = _parse_dt(m.get("dateTimeGMT", ""))
            return dt or datetime.min.replace(tzinfo=timezone.utc)

        completed.sort(key=_key, reverse=True)
        completed = completed[:count]

        lines = [f"✅ RECENT IPL 2026 RESULTS  (latest {len(completed)})\n" + "═" * 46]
        for m in completed:
            lines.append(
                f"\n🏆 {m.get('name','')}\n"
                f"   Match ID : {m.get('id','N/A')}\n"
                f"   Score    : {_fmt_score(m.get('score',[]))}\n"
                f"   Result   : {m.get('status','N/A')}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def get_ipl_scorecard(match_id: str) -> str:
    """
    Full batting and bowling scorecard for a match.
    Get Match ID from get_ipl_recent() or get_ipl_live_now().

    Args:
        match_id: e.g. 'a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
    """
    try:
        data = _raw_get("match_scorecard", {"id": match_id})
        sc   = data.get("data", {})
        if not sc:
            return f"No scorecard for match ID: {match_id}"

        lines = [
            f"📋 SCORECARD: {sc.get('name', match_id)}\n"
            f"   {sc.get('status','')}\n" + "═" * 52
        ]
        for inn in sc.get("scorecard", []):
            lines.append(f"\n🏏 {inn.get('inning','Innings')}")
            lines.append(f"{'Batter':<24} {'R':<5} {'B':<5} {'4s':<4} {'6s':<4} SR")
            lines.append("─" * 52)
            for b in inn.get("batting", []):
                nm = b.get("batsman", {}).get("name", "")[:22]
                lines.append(f"{nm:<24} {b.get('r',0):<5} {b.get('b',0):<5} {b.get('4s',0):<4} {b.get('6s',0):<4} {b.get('sr',0)}")
            lines.append(f"\n{'Bowler':<24} {'O':<5} {'M':<4} {'R':<5} {'W':<4} Eco")
            lines.append("─" * 52)
            for bw in inn.get("bowling", []):
                nm = bw.get("bowler", {}).get("name", "")[:22]
                lines.append(f"{nm:<24} {bw.get('o',0):<5} {bw.get('m',0):<4} {bw.get('r',0):<5} {bw.get('w',0):<4} {bw.get('eco',0)}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


@mcp.tool()
def search_ipl_player(player_name: str) -> str:
    """
    Search for a cricket player — profile, stats, IPL teams.

    Args:
        player_name: e.g. 'Virat Kohli', 'Rohit Sharma', 'Sanju Samson'
    """
    try:
        data    = _raw_get("players", {"search": player_name, "offset": 0})
        players = data.get("data", [])
        if not players:
            return f"No player found for '{player_name}'."

        p    = players[0]
        pid  = p.get("id", "")
        lines = [f"🏏 {p.get('name', player_name)}\n" + "═" * 44,
                 f"Country : {p.get('country','N/A')}"]

        if pid:
            info = _raw_get("players_info", {"id": pid}).get("data", {})
            for label, key in [("Date of Birth","dateOfBirth"),("Role","role"),
                                ("Batting","battingStyle"),("Bowling","bowlingStyle"),
                                ("Born","placeOfBirth"),("Teams","teams")]:
                val = info.get(key, "")
                if isinstance(val, list): val = ", ".join(val)
                if val: lines.append(f"{label:<16}: {val}")
            for s in info.get("stats", [])[:8]:
                fn, val = s.get("fn",""), s.get("value","")
                if fn and val: lines.append(f"  {fn:<32} {val}")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Error: {e}"


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not API_KEY:
        print("⚠️  CRICAPI_KEY not set — tools will return errors.", file=sys.stderr)
    mcp.run(transport="stdio")