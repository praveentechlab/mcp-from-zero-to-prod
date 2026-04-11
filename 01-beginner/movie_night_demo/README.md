# Movie Night Demo

A demonstration of the **Model Context Protocol (MCP)** featuring a movie night recommendation system. This project showcases how to build an MCP server with tools, resources, and prompts, and how to interact with it using a client.

## Overview

This project consists of two main components:

- **`movie_night_server.py`** - An MCP server that provides movie recommendations and related functionality
- **`movie_night_client.py`** - An MCP client that demonstrates how to use the server's capabilities

## Project Structure

```
movie_night_demo/
├── movie_night_server.py    # MCP Server implementation
├── movie_night_client.py    # MCP Client implementation
└── README.md               # This file
```

## Features

### Server Features (`movie_night_server.py`)

The server exposes three types of MCP capabilities:

#### 1. **Tools**
Interactive functions that accept user input and return results:

- **`find_movies(query, family_mode)`** - Search movies by title or genre
  - `query`: Search term (title or genre)
  - `family_mode`: Boolean to filter family-friendly movies only
  - Returns: List of matching movies with details (duration, rating, availability)

- **`suggest_snack(movie_title)`** - Get themed snack recommendations
  - `movie_title`: Movie title to get a snack suggestion for
  - Returns: Fun, thematic snack idea paired with the movie

#### 2. **Resources**
Read-only data exposed via URIs:

- **`movies://catalog`** - Full movie night catalog
  - Contains: All movies, total count, and availability status
  - Returns: JSON with complete movie database

- **`movies://family`** - Family-friendly movies only
  - Contains: Only movies marked as family-friendly
  - Returns: JSON array of family movies

#### 3. **Prompts**
Reusable AI instruction templates:

- **`movie_night_prompt(mood, max_duration)`** - Movie night planning prompt
  - `mood`: Desired movie mood (e.g., "fun family sci-fi")
  - `max_duration`: Maximum movie duration in minutes (default: 120)
  - Returns: AI-friendly prompt for generating movie recommendations

### Client Features (`movie_night_client.py`)

The client demonstrates all three MCP capabilities:

- **Demo 1 - Tools**: Lists available tools and calls `find_movies` and `suggest_snack`
- **Demo 2 - Resources**: Lists available resources and reads both movie resources
- **Demo 3 - Prompts**: Lists available prompts and generates a customized movie night prompt

## Sample Movie Database

The server includes 5 sample movies:

| Title | Genre | Duration | Family | Rating | Available |
|-------|-------|----------|--------|--------|-----------|
| Inception | Sci-Fi | 148 min | No | 4.8/5 | ✓ |
| Inside Out | Animation | 95 min | Yes | 4.7/5 | ✓ |
| Interstellar | Sci-Fi | 169 min | No | 4.9/5 | ✗ |
| The Martian | Sci-Fi | 144 min | Yes | 4.6/5 | ✓ |
| Coco | Animation | 105 min | Yes | 4.8/5 | ✓ |

## Usage

### Prerequisites

- Python 3.7+
- MCP SDK (`mcp` package)

### Installation

```bash
# Install dependencies
pip install mcp
```

### Running the Demo

1. **Start the client** (which will automatically start the server):

```bash
python movie_night_client.py
```

The client will:
- Connect to the server via stdio
- Display available tools, resources, and prompts
- Execute demo operations showing each capability
- Display formatted output for each demo section

### Output Example

```
============================================================
MCP MOVIE NIGHT DEMO
============================================================
Starting demo_mcp_server.py through stdio...
Connected successfully.

============================================================
3. PROMPTS DEMO
============================================================
Prompts are reusable AI instructions. They return message text for a model.

Available prompts:
  - movie_night_prompt: Prompt template for asking an AI to recommend a movie night plan.

[Generated prompt]
  You are a helpful movie night planner.
  ...
```

## MCP Concepts Demonstrated

This project is an educational resource for learning MCP:

1. **Tools** - How to expose callable functions with typed parameters
2. **Resources** - How to expose read-only data via URI schemes
3. **Prompts** - How to create reusable AI instruction templates
4. **Client-Server Communication** - How to connect and interact via stdio

## Customization

### Adding New Movies

Edit the `MOVIES` list in `movie_night_server.py`:

```python
MOVIES = [
    {
        "id": 6,
        "title": "Your Movie",
        "genre": "Your Genre",
        "duration_min": 120,
        "family_friendly": True,
        "rating": 4.5,
        "available": True,
    },
    # ... more movies
]
```

### Modifying the Movie Prompt

Edit the `movie_night_prompt()` function in `movie_night_server.py` to customize the AI prompt template.

### Adding New Tools

Use the `@mcp.tool()` decorator:

```python
@mcp.tool()
def your_tool(param1: str) -> str:
    """Description of what your tool does."""
    return "Result"
```

## Technical Details

- **Framework**: FastMCP (Model Context Protocol)
- **Communication**: Standard I/O (stdio)
- **Data Format**: JSON
- **Platform Support**: Windows, macOS, Linux

## References

- [Model Context Protocol (MCP) Documentation](https://modelcontextprotocol.io)
- [FastMCP Framework](https://github.com/jlooney/fastmcp)

## License

This is a demonstration project for educational purposes.
