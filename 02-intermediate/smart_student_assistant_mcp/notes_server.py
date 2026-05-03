import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)


BASE_DIR = Path(__file__).resolve().parent
NOTES_DIR = BASE_DIR / "notes"

"""
mcp = FastMCP(
    "student_notes_server",
)
"""
mcp = FastMCP(
    "student_notes_server",
    host="127.0.0.1",
    port=8102,
    streamable_http_path="/mcp",
)


def _safe_note_path(file_name: str) -> Path:
    candidate = (NOTES_DIR / file_name).resolve()
    if NOTES_DIR.resolve() not in candidate.parents and candidate != NOTES_DIR.resolve():
        raise ValueError("Invalid note path.")
    if candidate.suffix.lower() not in {".md", ".txt"}:
        raise ValueError("Only .md and .txt notes are supported.")
    if not candidate.exists():
        raise FileNotFoundError(f"Note not found: {file_name}")
    return candidate


@mcp.tool()
def list_notes(query: str = "") -> str:
    """List available notes, optionally filtering by file name or content."""
    q = query.lower().strip()
    notes = []

    for path in sorted(NOTES_DIR.glob("*")):
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        content = path.read_text(encoding="utf-8")
        haystack = f"{path.name}\n{content}".lower()
        if q and q not in haystack:
            continue
        notes.append(
            {
                "file_name": path.name,
                "title": content.splitlines()[0].lstrip("# ").strip() if content.splitlines() else path.stem,
                "size_chars": len(content),
            }
        )

    return json.dumps(
        {
            "source": "student_notes_server",
            "query": query,
            "notes": notes,
        },
        indent=2,
    )


@mcp.tool()
def read_note(file_name: str) -> str:
    """Read a specific student note by file name."""
    path = _safe_note_path(file_name)
    return json.dumps(
        {
            "source": "student_notes_server",
            "file_name": path.name,
            "content": path.read_text(encoding="utf-8"),
        },
        indent=2,
    )


if __name__ == "__main__":
    #mcp.run()
    mcp.run(transport="streamable-http")
