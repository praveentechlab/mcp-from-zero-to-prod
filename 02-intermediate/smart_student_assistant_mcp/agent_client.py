import asyncio
import json
import os
import queue
import socket
import subprocess
import sys
import threading
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = "gpt-4o-mini"

SERVERS = [
    {
        "name": "Calendar MCP Server",
        "script": "calendar_server.py",
        "port": 8101,
        "url": "http://127.0.0.1:8101/mcp",
    },
    {
        "name": "Notes MCP Server",
        "script": "notes_server.py",
        "port": 8102,
        "url": "http://127.0.0.1:8102/mcp",
    },
    {
        "name": "Practice Quiz MCP Server",
        "script": "quiz_server.py",
        "port": 8103,
        "url": "http://127.0.0.1:8103/mcp",
    },
]


def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


async def _wait_for_server(port: int, timeout_seconds: float = 10.0) -> None:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        if _is_port_open(port):
            return
        await asyncio.sleep(0.2)
    raise TimeoutError(f"Server on port {port} did not start within {timeout_seconds} seconds.")


def _start_servers() -> list[subprocess.Popen]:
    processes = []
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"

    for server in SERVERS:
        script_path = BASE_DIR / server["script"]
        process = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        processes.append(process)
    return processes


def _stop_servers(processes: list[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


def _text_content(result) -> str:
    if not result.content:
        return ""
    return result.content[0].text


def _extract_topics(note_payloads: list[dict]) -> list[str]:
    topics = []
    markers = ("- ", "* ")

    for payload in note_payloads:
        content = payload["content"]
        for line in content.splitlines():
            clean = line.strip()
            if clean.startswith(markers):
                topic = clean[2:].strip()
                if topic and topic not in topics:
                    topics.append(topic)

    return topics[:6]


def _load_env() -> None:
    if load_dotenv:
        load_dotenv(BASE_DIR / ".env")


def _openai_client():
    _load_env()
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is required. Create a .env file from .env.example and add your key."
        )
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError(
            "The openai package is required. Run: pip install -r requirements.txt"
        )
    return OpenAI()


def _json_from_response(response) -> dict:
    text = getattr(response, "output_text", "") or ""
    if not text:
        for item in getattr(response, "output", []) or []:
            for content in getattr(item, "content", []) or []:
                if getattr(content, "type", "") == "output_text":
                    text += getattr(content, "text", "")
    return json.loads(text)


def _llm_intent_plan(question: str) -> tuple[dict, str]:
    client = _openai_client()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    system_prompt = """
You are the intent planner for a Smart Student Assistant MCP demo.
Return only valid JSON. No markdown.

Available MCP capabilities:
- Calendar: upcoming events and exams.
- Notes: list/read AI notes by query.
- Quiz: generate practice questions or revision tips from topics.
- OpenAI: create a study plan from calendar and notes context.

Choose only the tools needed for the student's query.
Schema:
{
  "intent": "calendar|notes|plan|quiz|full_preparation",
  "needs_calendar": boolean,
  "needs_notes": boolean,
  "needs_plan": boolean,
  "needs_quiz": boolean,
  "topic_query": string,
  "available_hours": number,
  "quiz_count": integer,
  "reason": string
}
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError(
            "OpenAI intent request failed. Check your internet connection, OPENAI_API_KEY, "
            f"and OPENAI_MODEL in .env. Original error: {exc}"
        ) from exc
    plan = json.loads(response.choices[0].message.content)

    required = {
        "intent",
        "needs_calendar",
        "needs_notes",
        "needs_plan",
        "needs_quiz",
        "topic_query",
        "available_hours",
        "quiz_count",
        "reason",
    }
    missing = sorted(required - set(plan))
    if missing:
        raise RuntimeError(f"OpenAI intent response missed required field(s): {', '.join(missing)}")

    return plan, f"OpenAI model: {model}"


def _topic_summary_from_notes(note_payloads: list[dict]) -> str:
    if not note_payloads:
        return "No matching notes were found."

    lines = []
    for payload in note_payloads:
        title = payload["content"].splitlines()[0].lstrip("# ").strip()
        lines.append(f"{title}:")
        for topic in _extract_topics([payload])[:4]:
            lines.append(f"- {topic}")
    return "\n".join(lines)


def _llm_final_answer(question: str, intent_plan: dict, context: dict) -> tuple[str, str]:
    client = _openai_client()
    model = os.getenv("OPENAI_MODEL", DEFAULT_MODEL)
    system_prompt = """
You are a helpful Smart Student Assistant.
Use only the provided MCP context.
Answer based on the user's intent.
If the user asked only for a quiz, do not include a full study timetable.
If the user asked only for calendar info, do not include notes or quiz content.
If the intent plan has needs_plan=true, create the study plan yourself from the exam details,
available hours, and extracted note topics. There is no Planner MCP server.
Keep the response concise and classroom-demo friendly.
"""
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "student_question": question,
                            "intent_plan": intent_plan,
                            "mcp_context": context,
                        },
                        indent=2,
                    ),
                },
            ],
        )
    except Exception as exc:
        raise RuntimeError(
            "OpenAI final response request failed. Check your internet connection, OPENAI_API_KEY, "
            f"and OPENAI_MODEL in .env. Original error: {exc}"
        ) from exc
    return response.choices[0].message.content.strip(), f"OpenAI model: {model}"


async def _connect_sessions(stack: AsyncExitStack) -> dict[str, ClientSession]:
    sessions = {}

    for server in SERVERS:
        read_stream, write_stream, _ = await stack.enter_async_context(
            streamablehttp_client(server["url"], terminate_on_close=False)
        )
        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        sessions[server["name"]] = session

    return sessions


def _console_log(text: str = "", tag: str = "normal") -> None:
    print(text)


def _friendly_error(exc: BaseException) -> str:
    if isinstance(exc, BaseExceptionGroup):
        messages = [_friendly_error(item) for item in exc.exceptions]
        unique_messages = list(dict.fromkeys(message for message in messages if message))
        return "\n".join(unique_messages) or str(exc)
    return str(exc) or exc.__class__.__name__


async def run_demo(question: str, log=_console_log) -> dict:
    log("\nSMART STUDENT ASSISTANT - MULTI-SERVER MCP DEMO", "title")
    log("=" * 62, "muted")
    log(f"Student question: {question}\n", "student")

    log("0) Agent asks OpenAI LLM to understand the query intent...", "step")
    intent_plan, intent_source = _llm_intent_plan(question)
    log(f"   Intent: {intent_plan['intent']} ({intent_source})", "success")
    log(f"   Reason: {intent_plan['reason']}\n", "muted")

    context = {
        "exam": None,
        "calendar_events": [],
        "notes": [],
        "note_summary": "",
        "topics": [],
        "study_plan_request": None,
        "quiz": [],
        "servers_used": [],
    }

    processes = _start_servers()
    try:
        for server in SERVERS:
            await _wait_for_server(server["port"])

        async with AsyncExitStack() as stack:
            sessions = await _connect_sessions(stack)
            step_number = 1

            if intent_plan.get("needs_calendar"):
                log(f"{step_number}) Agent asks Calendar MCP Server for upcoming events...", "step")
                calendar_result = await sessions["Calendar MCP Server"].call_tool(
                    "get_upcoming_events",
                    {"days_ahead": 2},
                )
                calendar_data = json.loads(_text_content(calendar_result))
                context["calendar_events"] = calendar_data["events"]
                context["exam"] = next(
                    (
                        event
                        for event in calendar_data["events"]
                        if "exam" in event["title"].lower()
                    ),
                    calendar_data["events"][0] if calendar_data["events"] else None,
                )
                if context["exam"]:
                    exam = context["exam"]
                    log(f"   Found event: {exam['title']} at {exam['start']} in {exam['location']}", "success")
                context["servers_used"].append("Calendar MCP Server")
                log("")
                step_number += 1

            if intent_plan.get("needs_notes"):
                topic_query = intent_plan.get("topic_query") or "AI"
                log(f"{step_number}) Agent asks Notes MCP Server for notes matching {topic_query!r}...", "step")
                notes_result = await sessions["Notes MCP Server"].call_tool(
                    "list_notes",
                    {"query": topic_query},
                )
                notes_data = json.loads(_text_content(notes_result))
                selected_notes = notes_data["notes"]
                if not selected_notes and topic_query.lower() != "ai":
                    notes_result = await sessions["Notes MCP Server"].call_tool(
                        "list_notes",
                        {"query": "AI"},
                    )
                    notes_data = json.loads(_text_content(notes_result))
                    selected_notes = notes_data["notes"]
                context["notes"] = selected_notes
                log("   Notes found:", "muted")
                for note in selected_notes:
                    log(f"   - {note['file_name']}: {note['title']}", "note")
                log("")
                step_number += 1

                log(f"{step_number}) Agent reads selected notes and extracts matching topics...", "step")
                note_payloads = []
                for note in selected_notes:
                    read_result = await sessions["Notes MCP Server"].call_tool(
                        "read_note",
                        {"file_name": note["file_name"]},
                    )
                    note_payloads.append(json.loads(_text_content(read_result)))

                context["topics"] = _extract_topics(note_payloads)
                context["note_summary"] = _topic_summary_from_notes(note_payloads)
                for topic in context["topics"]:
                    log(f"   - {topic}", "topic")
                context["servers_used"].append("Notes MCP Server")
                log("")
                step_number += 1

            if intent_plan.get("needs_plan"):
                if not context["exam"]:
                    log(f"{step_number}) Study planning needs exam time, so agent asks Calendar MCP Server...", "step")
                    calendar_result = await sessions["Calendar MCP Server"].call_tool(
                        "get_upcoming_events",
                        {"days_ahead": 2},
                    )
                    calendar_data = json.loads(_text_content(calendar_result))
                    context["calendar_events"] = calendar_data["events"]
                    context["exam"] = next(
                        (
                            event
                            for event in calendar_data["events"]
                            if "exam" in event["title"].lower()
                        ),
                        calendar_data["events"][0] if calendar_data["events"] else None,
                    )
                    if "Calendar MCP Server" not in context["servers_used"]:
                        context["servers_used"].append("Calendar MCP Server")
                    step_number += 1

                context["study_plan_request"] = {
                    "created_by": "OpenAI final response",
                    "available_hours": float(intent_plan.get("available_hours") or 4),
                    "exam": context["exam"],
                    "topics": context["topics"],
                }
                log(f"{step_number}) Agent keeps study-plan generation for OpenAI reasoning...", "step")
                log(
                    f"   OpenAI will create a {context['study_plan_request']['available_hours']}-hour plan from Calendar + Notes context.",
                    "plan",
                )
                log("")
                step_number += 1

            if intent_plan.get("needs_quiz"):
                if not context["topics"]:
                    context["topics"] = [intent_plan.get("topic_query") or "AI basics"]
                quiz_count = int(intent_plan.get("quiz_count") or 3)
                log(f"{step_number}) Agent asks Practice Quiz MCP Server for {quiz_count} question(s)...", "step")
                quiz_result = await sessions["Practice Quiz MCP Server"].call_tool(
                    "generate_quiz",
                    {
                        "topics_json": json.dumps(context["topics"]),
                        "question_count": quiz_count,
                    },
                )
                quiz_data = json.loads(_text_content(quiz_result))
                context["quiz"] = quiz_data["questions"]
                for quiz_question in context["quiz"]:
                    log(f"   Q{quiz_question['number']}. {quiz_question['question']}", "quiz")
                context["servers_used"].append("Practice Quiz MCP Server")
                log("")

    finally:
        _stop_servers(processes)

    log("Final) Agent asks OpenAI LLM to compose an intent-specific answer...", "step")
    final_answer, answer_source = _llm_final_answer(question, intent_plan, context)
    log(f"   Final answer source: {answer_source}", "muted")

    log("\nFINAL ASSISTANT RESPONSE", "title")
    log("=" * 62, "muted")
    for line in final_answer.splitlines():
        log(line, "success" if line.strip().startswith(("Intent", "Upcoming")) else "normal")

    log("\nMCP servers used:", "heading")
    for server_name in dict.fromkeys(context["servers_used"]):
        server = next(item for item in SERVERS if item["name"] == server_name)
        log(f"- {server['name']} ({server['url']})", "server")

    return {
        "intent_plan": intent_plan,
        "context": context,
        "final_answer": final_answer,
        "servers": SERVERS,
    }


def run_ui() -> None:
    import tkinter as tk
    from tkinter import messagebox, ttk

    root = tk.Tk()
    root.title("Smart Student Assistant - MCP Multi-Server Demo")
    root.geometry("1060x760")
    root.minsize(930, 660)
    root.configure(bg="#f4f7fb")

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Accent.TButton", background="#2563eb", foreground="white", font=("Segoe UI", 10, "bold"))
    style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#9ca3af")])

    messages = queue.Queue()
    running = {"value": False}

    def card(parent, title, body, color, column):
        frame = tk.Frame(parent, bg="white", highlightbackground=color, highlightthickness=2)
        frame.grid(row=0, column=column, sticky="nsew", padx=8, pady=8)
        tk.Label(frame, text=title, bg=color, fg="white", font=("Segoe UI", 10, "bold"), padx=10, pady=5).pack(fill="x")
        tk.Label(frame, text=body, bg="white", fg="#1f2937", font=("Segoe UI", 9), padx=10, pady=10, wraplength=250, justify="left").pack(fill="both", expand=True)
        return frame

    header = tk.Frame(root, bg="#172554", padx=18, pady=16)
    header.pack(fill="x")

    brand_label = tk.Label(
        header,
        text="PraveenTechlab",
        bg="#172554",
        fg="#fde68a",
        font=("Segoe UI", 12, "bold"),
    )
    brand_label.pack(side="right", anchor="ne")

    header_left = tk.Frame(header, bg="#172554")
    header_left.pack(side="left", fill="x", expand=True)

    app_icon = tk.Canvas(
        header_left,
        width=72,
        height=72,
        bg="#172554",
        highlightthickness=0,
    )
    app_icon.pack(side="left", padx=(0, 14), pady=(0, 2))
    app_icon.create_oval(6, 6, 66, 66, fill="#0ea5e9", outline="#dbeafe", width=3)
    app_icon.create_rectangle(20, 30, 51, 50, fill="#fef3c7", outline="#082f49", width=2)
    app_icon.create_polygon(20, 30, 35, 20, 51, 30, fill="#fb923c", outline="#082f49")
    app_icon.create_line(35, 20, 35, 50, fill="#082f49", width=2)
    app_icon.create_oval(29, 11, 42, 24, fill="#facc15", outline="#082f49", width=1)
    app_icon.create_line(18, 56, 54, 56, fill="#bfdbfe", width=3)

    title_block = tk.Frame(header_left, bg="#172554")
    title_block.pack(side="left", anchor="w")

    tk.Label(
        title_block,
        text="Smart Student Assistant",
        bg="#172554",
        fg="white",
        font=("Segoe UI", 22, "bold"),
    ).pack(anchor="w")

    tk.Label(
        title_block,
        text="Multi-Server MCP demo using Streamable HTTP",
        bg="#172554",
        fg="#bfdbfe",
        font=("Segoe UI", 11),
    ).pack(anchor="w", pady=(4, 0))

    cards = tk.Frame(root, bg="#f4f7fb", padx=10, pady=8)
    cards.pack(fill="x")
    for index in range(3):
        cards.grid_columnconfigure(index, weight=1)
    card(cards, "Calendar Server", "Finds the AI exam from upcoming student events.", "#0ea5e9", 0)
    card(cards, "Notes Server", "Reads real markdown notes from the notes folder.", "#10b981", 1)
    card(cards, "Quiz Server", "Generates quick practice questions from extracted topics.", "#8b5cf6", 2)

    control = tk.Frame(root, bg="#f4f7fb", padx=18, pady=8)
    control.pack(fill="x")
    tk.Label(control, text="Student question", bg="#f4f7fb", fg="#111827", font=("Segoe UI", 10, "bold")).pack(anchor="w")
    question_var = tk.StringVar(value="Help me prepare for my AI exam tomorrow.")
    question_entry = ttk.Entry(control, textvariable=question_var, font=("Segoe UI", 11))
    question_entry.pack(side="left", fill="x", expand=True, ipady=5, pady=(6, 0))

    run_button = ttk.Button(control, text="Run Demo", style="Accent.TButton")
    run_button.pack(side="left", padx=(10, 0), pady=(6, 0), ipady=4)

    status_var = tk.StringVar(value="Ready")
    status = tk.Label(root, textvariable=status_var, bg="#e0f2fe", fg="#075985", font=("Segoe UI", 10, "bold"), anchor="w", padx=18, pady=6)
    status.pack(fill="x", padx=18, pady=(8, 0))

    output_frame = tk.Frame(root, bg="#111827", padx=10, pady=10)
    output_frame.pack(fill="both", expand=True, padx=18, pady=14)

    output = tk.Text(
        output_frame,
        bg="#0b1220",
        fg="#e5e7eb",
        insertbackground="white",
        relief="flat",
        wrap="word",
        font=("Consolas", 10),
        padx=12,
        pady=12,
    )
    output.pack(side="left", fill="both", expand=True)
    scroll = ttk.Scrollbar(output_frame, orient="vertical", command=output.yview)
    scroll.pack(side="right", fill="y")
    output.configure(yscrollcommand=scroll.set)

    tag_colors = {
        "title": "#93c5fd",
        "muted": "#94a3b8",
        "student": "#fde68a",
        "step": "#38bdf8",
        "success": "#86efac",
        "note": "#c4b5fd",
        "topic": "#fca5a5",
        "heading": "#fdba74",
        "plan": "#fef08a",
        "quiz": "#ddd6fe",
        "server": "#67e8f9",
        "error": "#f87171",
    }
    for tag, color in tag_colors.items():
        font = ("Consolas", 10, "bold") if tag in {"title", "step", "heading", "error"} else ("Consolas", 10)
        output.tag_configure(tag, foreground=color, font=font)

    def append_line(text, tag="normal"):
        output.configure(state="normal")
        output.insert("end", text + "\n", tag)
        output.see("end")
        output.configure(state="disabled")

    def worker(question):
        def log(text="", tag="normal"):
            messages.put(("log", text, tag))

        try:
            # On Windows, asyncio.run() inside a non-main thread crashes with
            # ProactorEventLoop. Explicitly create a SelectorEventLoop which
            # is thread-safe and works on all platforms.
            if sys.platform == "win32":
                loop = asyncio.SelectorEventLoop()
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(run_demo(question, log=log))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
            messages.put(("done", "Demo completed successfully.", "success"))
        except Exception as exc:
            messages.put(("done", f"Demo failed: {_friendly_error(exc)}", "error"))

    def start_demo():
        if running["value"]:
            return
        output.configure(state="normal")
        output.delete("1.0", "end")
        output.configure(state="disabled")
        running["value"] = True
        run_button.configure(state="disabled")
        status_var.set("Running MCP servers and connecting over Streamable HTTP...")
        thread = threading.Thread(target=worker, args=(question_var.get().strip(),), daemon=True)
        thread.start()

    def poll_messages():
        try:
            while True:
                kind, text, tag = messages.get_nowait()
                append_line(text, tag)
                if kind == "done":
                    running["value"] = False
                    run_button.configure(state="normal")
                    status_var.set(text)
        except queue.Empty:
            pass
        root.after(100, poll_messages)

    def on_close():
        if running["value"] and not messagebox.askyesno("Close demo?", "The demo is still running. Close the window anyway?"):
            return
        root.destroy()

    run_button.configure(command=start_demo)
    question_entry.bind("<Return>", lambda _event: start_demo())
    root.protocol("WM_DELETE_WINDOW", on_close)
    append_line("Ready. Click Run Demo to start the multi-server MCP flow.", "success")
    poll_messages()
    root.mainloop()


if __name__ == "__main__":
    # On Windows, the default ProactorEventLoop does not support all asyncio
    # features used by the MCP HTTP client. Switch to SelectorEventLoop.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    user_question = "Help me prepare for my AI exam tomorrow."
    args = sys.argv[1:]
    if "--ui" in args:
        run_ui()
    else:
        if args:
            user_question = " ".join(arg for arg in args if arg != "--cli")
        try:
            asyncio.run(run_demo(user_question))
        except Exception as exc:
            print(f"\nDemo failed: {_friendly_error(exc)}")
            sys.exit(1)