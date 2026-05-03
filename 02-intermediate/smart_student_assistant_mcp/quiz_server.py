import json
import sys

from mcp.server.fastmcp import FastMCP


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)


mcp = FastMCP(
    "student_quiz_server",
    host="127.0.0.1",
    port=8103,
    streamable_http_path="/mcp",
)


@mcp.tool()
def generate_quiz(topics_json: str, question_count: int = 3) -> str:
    """Generate a short practice quiz from study topics."""
    topics = json.loads(topics_json)
    if not isinstance(topics, list) or not topics:
        topics = ["AI basics", "Search algorithms", "Neural networks"]

    questions = []
    for index, topic in enumerate(topics[:question_count], start=1):
        questions.append(
            {
                "number": index,
                "topic": topic,
                "question": f"Explain this topic in two or three sentences: {topic}",
                "revision_tip": f"Use one definition, one example, and one exam keyword for {topic}.",
            }
        )

    return json.dumps(
        {
            "source": "student_quiz_server",
            "question_count": len(questions),
            "questions": questions,
        },
        indent=2,
    )


@mcp.tool()
def get_revision_tip(topic: str) -> str:
    """Return a quick revision tip for one topic."""
    clean_topic = topic.strip() or "this topic"
    return json.dumps(
        {
            "source": "student_quiz_server",
            "topic": clean_topic,
            "tip": f"Revise {clean_topic} by writing a short definition, drawing one example, and solving one quick practice question.",
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
