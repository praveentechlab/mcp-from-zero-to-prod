import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("movie_night_demo")

MOVIES = [
    {
        "id": 1,
        "title": "Inception",
        "genre": "Sci-Fi",
        "duration_min": 148,
        "family_friendly": False,
        "rating": 4.8,
        "available": True,
    },
    {
        "id": 2,
        "title": "Inside Out",
        "genre": "Animation",
        "duration_min": 95,
        "family_friendly": True,
        "rating": 4.7,
        "available": True,
    },
    {
        "id": 3,
        "title": "Interstellar",
        "genre": "Sci-Fi",
        "duration_min": 169,
        "family_friendly": False,
        "rating": 4.9,
        "available": False,
    },
    {
        "id": 4,
        "title": "The Martian",
        "genre": "Sci-Fi",
        "duration_min": 144,
        "family_friendly": True,
        "rating": 4.6,
        "available": True,
    },
    {
        "id": 5,
        "title": "Coco",
        "genre": "Animation",
        "duration_min": 105,
        "family_friendly": True,
        "rating": 4.8,
        "available": True,
    },
]

@mcp.tool()
def find_movies(query: str, family_mode: bool = False) -> str:
    """Search movies by title or genre."""
    q = query.lower().strip()
    matches = []

    for movie in MOVIES:
        if family_mode and not movie["family_friendly"]:
            continue
        if q in movie["title"].lower() or q in movie["genre"].lower():
            matches.append(movie)

    if not matches:
        return f"No movies found for query={query!r} with family_mode={family_mode}."

    lines = [f"Found {len(matches)} movie(s):", ""]
    for movie in matches:
        status = "Available" if movie["available"] else "Unavailable"
        lines.append(f"- {movie['title']} ({movie['genre']})")
        lines.append(f"  Duration : {movie['duration_min']} min")
        lines.append(f"  Rating   : {movie['rating']}/5")
        lines.append(f"  Family   : {movie['family_friendly']}")
        lines.append(f"  Status   : {status}")
        lines.append("")
    return "\n".join(lines).strip()

@mcp.tool()
def suggest_snack(movie_title: str) -> str:
    """Return a fun themed snack suggestion for a movie."""
    title = movie_title.lower().strip()

    if "inception" in title:
        return "Snack idea: layered brownies, because the movie has layers inside layers."
    if "interstellar" in title or "martian" in title:
        return "Snack idea: astronaut popcorn and orange soda for a space vibe."
    if "inside out" in title or "coco" in title:
        return "Snack idea: colorful fruit cups and mini churros."
    return "Snack idea: classic popcorn with a drink combo."

@mcp.resource("movies://catalog")
def movie_catalog() -> str:
    """Full movie night catalog."""
    payload = {
        "collection": "Movie Night Demo Catalog",
        "total_movies": len(MOVIES),
        "available_now": sum(1 for movie in MOVIES if movie["available"]),
        "movies": MOVIES,
    }
    return json.dumps(payload, indent=2)

@mcp.resource("movies://family")
def family_movies() -> str:
    """Only family-friendly movies."""
    payload = [movie for movie in MOVIES if movie["family_friendly"]]
    return json.dumps(payload, indent=2)

@mcp.prompt()
def movie_night_prompt(mood: str, max_duration: int = 120) -> str:
    """Prompt template for asking an AI to recommend a movie night plan."""
    return f"""You are a helpful movie night planner.

User mood: {mood}
Maximum duration: {max_duration} minutes

Available movie catalog:
{json.dumps(MOVIES, indent=2)}

Instructions:
- Recommend up to 2 movies that match the mood.
- Only pick movies with duration <= {max_duration}.
- Prefer available titles.
- Include one short reason for each choice.
- Suggest one matching snack idea for the top choice.
"""



if __name__ == "__main__":
    mcp.run()





