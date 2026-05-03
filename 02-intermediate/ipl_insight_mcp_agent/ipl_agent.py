"""
IPL Insight Agent
=================
Single-file app with:
1. IPLAgent   -> MCP client + OpenAI tool loop
2. IPLApp     -> Tkinter UI

Available tools:
  get_ipl_live_now    — live match scores
  get_ipl_recent      — recent completed results
  get_ipl_scorecard   — full batting/bowling scorecard
  search_ipl_player   — player profile & stats

Run:
    python ipl_agent.py

Optional CLI smoke test:
    python ipl_agent.py --cli
"""

import asyncio
import json
import os
import sys
import threading
import tkinter as tk
from contextlib import AsyncExitStack
from tkinter import messagebox, scrolledtext
from typing import Any, Callable, Coroutine

from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CRICAPI_KEY    = os.getenv("CRICAPI_KEY", "")
LLM_MODEL      = "gpt-4o-mini"
MAX_TOOL_TURNS = 6

SYSTEM_PROMPT = """\
You are the IPL Insight Agent, a cricket expert for IPL 2026.
Always use the provided tools to fetch live data before answering.

Tool routing:
- Live scores  -> get_ipl_live_now
- Past results -> get_ipl_recent
- Scorecard    -> get_ipl_scorecard (needs match_id from get_ipl_recent or get_ipl_live_now)
- Player info  -> search_ipl_player

Output rules:
1. Output plain text only.
2. The tool already formats output with lines and spacing. Preserve it.
3. Always include Match ID exactly as it appears in tool output.
4. Prefer get_ipl_recent to find a match_id before calling get_ipl_scorecard.
5. Do not invent data.
6. Keep answers concise and helpful.
"""


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _tool_to_openai(tool) -> dict:
    schema = tool.inputSchema or {}
    return {
        "type": "function",
        "function": {
            "name":        tool.name,
            "description": tool.description or "",
            "parameters": {
                "type":       "object",
                "properties": schema.get("properties", {}),
                "required":   schema.get("required", []),
            },
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Async agent
# ─────────────────────────────────────────────────────────────────────────────

class IPLAgent:
    def __init__(self):
        if not OPENAI_API_KEY:
            raise EnvironmentError("OPENAI_API_KEY is not set.")

        self.llm = AsyncOpenAI(api_key=OPENAI_API_KEY)
        server_script = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "ipl_mcp_server.py"
        )
        self._server_params = StdioServerParameters(
            command=sys.executable,
            args=["-u", server_script],
            env={
                **os.environ,
                "CRICAPI_KEY":      CRICAPI_KEY,
                "PYTHONUNBUFFERED": "1",
                "PYTHONIOENCODING": "utf-8",
            },
        )
        self._exit_stack: AsyncExitStack | None = None
        self._session:    ClientSession | None = None
        self._openai_tools: list[dict] = []
        self._ready = False

    async def start(self):
        self._exit_stack = AsyncExitStack()
        read, write = await self._exit_stack.enter_async_context(
            stdio_client(self._server_params)
        )
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read, write)
        )
        await self._session.initialize()
        tools = await self._session.list_tools()
        self._openai_tools = [_tool_to_openai(t) for t in tools.tools]
        self._ready = True

    async def stop(self):
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session    = None
            self._ready      = False

    async def chat(
        self,
        user_query: str,
        on_tool_call: Callable[[str, dict, str], Coroutine] | None = None,
    ) -> str:
        if not self._ready:
            raise RuntimeError("Agent not started.")

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_query},
        ]

        for _ in range(MAX_TOOL_TURNS):
            response = await self.llm.chat.completions.create(
                model=LLM_MODEL,
                messages=messages,
                tools=self._openai_tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                return msg.content or "(No response)"

            messages.append(msg.model_dump(exclude_unset=True))

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                try:
                    fn_args: dict[str, Any] = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    fn_args = {}

                try:
                    result      = await self._session.call_tool(fn_name, fn_args)
                    result_text = "".join(
                        b.text for b in result.content if hasattr(b, "text")
                    )
                except Exception as exc:
                    result_text = f"Tool error: {exc}"

                if on_tool_call:
                    await on_tool_call(fn_name, fn_args, result_text)

                messages.append({
                    "role":         "tool",
                    "tool_call_id": tc.id,
                    "content":      result_text,
                })

        final = await self.llm.chat.completions.create(
            model=LLM_MODEL, messages=messages,
        )
        return final.choices[0].message.content or "(No response)"


# ─────────────────────────────────────────────────────────────────────────────
# Tkinter UI
# ─────────────────────────────────────────────────────────────────────────────

# Colour palette
_C = {
    "bg":         "#f0f4fc",
    "header":     "#1a2f6e",
    "accent":     "#2563eb",
    "accent_dk":  "#1d4ed8",
    "gold":       "#f59e0b",
    "live_red":   "#dc2626",
    "card_bg":    "#ffffff",
    "border":     "#cbd5e1",
    "text":       "#1e293b",
    "muted":      "#64748b",
    "status_bg":  "#dbeafe",
    "status_fg":  "#1e40af",
    "tool_bg":    "#fef9c3",
    "tool_fg":    "#78350f",
}

# Quick-action buttons: (label, emoji, query, bg_colour)
_QUICK = [
    ("Live Now",       "🔴", "Are there any live IPL 2026 matches right now? Show scores and overs.",                 _C["live_red"]),
    ("Recent Results", "✅", "Show me the most recent 5 IPL 2026 match results with winners and Match IDs.",          "#16a34a"),
    ("Scorecard",      "📋", "Show the full scorecard for the most recent completed IPL 2026 match.",                 "#7c3aed"),
    ("Player Search",  "🏏", "Tell me about Virat Kohli — profile, batting style, teams, and career stats.",          _C["accent"]),
]


class IPLApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("IPL Insight Agent 2026")
        self.geometry("960x700")
        self.minsize(800, 560)
        self.configure(bg=_C["bg"])

        self._loop   = asyncio.new_event_loop()
        self._agent: IPLAgent | None = None
        self._ready   = False
        self._loading = False

        self._build_ui()

        self._bg_thread = threading.Thread(target=self._loop.run_forever, daemon=True)
        self._bg_thread.start()

        self._set_status("Connecting to MCP server…")
        asyncio.run_coroutine_threadsafe(self._start_agent(), self._loop)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── startup ──────────────────────────────────────────────────────────────

    async def _start_agent(self):
        try:
            self._agent = IPLAgent()
            await self._agent.start()
            self._ready = True
            self.after(0, lambda: self._set_status("Ready — ask anything about IPL 2026."))
            self.after(0, lambda: self._set_controls(True))
        except Exception as exc:
            self.after(0, lambda exc=exc: self._set_status(f"Startup error: {exc}"))
            self.after(
                0,
                lambda exc=exc: messagebox.showerror(
                    "Startup Error",
                    f"{str(exc)}\n\nTroubleshooting:\n"
                    "• Check CRICAPI_KEY and OPENAI_API_KEY in .env\n"
                    "• Ensure ipl_mcp_server.py is in the same folder\n"
                    '• Run: python -c "import ipl_mcp_server" to check imports',
                ),
            )

    # ── UI build ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_quick_buttons()
        self._build_input_row()
        self._build_output_area()
        self._build_status_bar()

        self._append_output(
            "Welcome to IPL Insight Agent 2026  🏏\n\n"
            "Use the quick-action buttons above or type your own question.\n"
            "Tip: Try 'Live Now' first — or search for any player by name!\n"
        )

    def _build_header(self):
        hdr = tk.Frame(self, bg=_C["header"])
        hdr.pack(fill=tk.X)

        inner = tk.Frame(hdr, bg=_C["header"], padx=20, pady=14)
        inner.pack(fill=tk.X)

        # Left: logo + title
        left = tk.Frame(inner, bg=_C["header"])
        left.pack(side=tk.LEFT)
        tk.Label(left, text="🏏", bg=_C["header"], fg="white",
                 font=("Segoe UI Emoji", 34)).pack(side=tk.LEFT, padx=(0, 10))
        txt = tk.Frame(left, bg=_C["header"])
        txt.pack(side=tk.LEFT)
        tk.Label(txt, text="IPL Insight Agent", bg=_C["header"], fg="white",
                 font=("Segoe UI", 22, "bold")).pack(anchor=tk.W)
        tk.Label(txt, text="Live cricket intelligence powered by AI  •  IPL 2026",
                 bg=_C["header"], fg="#93c5fd",
                 font=("Segoe UI", 10)).pack(anchor=tk.W)

        # Right: branding
        tk.Label(inner, text="PraveenTechLab", bg=_C["header"], fg=_C["gold"],
                 font=("Segoe UI", 12, "bold")).pack(side=tk.RIGHT)

        # Tool pills row
        pills = tk.Frame(hdr, bg="#162459", padx=20, pady=6)
        pills.pack(fill=tk.X)
        tk.Label(pills, text="Tools:", bg="#162459", fg="#93c5fd",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 8))
        for pill in ("get_ipl_live_now", "get_ipl_recent",
                     "get_ipl_scorecard", "search_ipl_player"):
            tk.Label(pills, text=pill, bg="#1e3a8a", fg="#bfdbfe",
                     font=("Consolas", 8), padx=6, pady=2,
                     relief=tk.FLAT).pack(side=tk.LEFT, padx=3)

    def _build_quick_buttons(self):
        outer = tk.Frame(self, bg=_C["bg"], padx=18, pady=10)
        outer.pack(fill=tk.X)

        tk.Label(outer, text="Quick Actions", bg=_C["bg"], fg=_C["header"],
                 font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 6))

        row = tk.Frame(outer, bg=_C["bg"])
        row.pack(fill=tk.X)

        self._quick_buttons: list[tk.Button] = []
        for label, emoji, query, colour in _QUICK:
            btn = tk.Button(
                row,
                text=f"{emoji}  {label}",
                font=("Segoe UI", 11, "bold"),
                bg=colour, fg="white",
                activebackground=colour, activeforeground="white",
                relief=tk.FLAT, padx=14, pady=8, cursor="hand2",
                command=lambda q=query: self._run_query(q),
                state=tk.DISABLED,
            )
            btn.pack(side=tk.LEFT, padx=(0, 8))
            self._quick_buttons.append(btn)

    def _build_input_row(self):
        outer = tk.Frame(self, bg=_C["bg"], padx=18, pady=0)
        outer.pack(fill=tk.X)

        frame = tk.Frame(outer, bg=_C["card_bg"], relief=tk.FLAT,
                         highlightthickness=1,
                         highlightbackground=_C["border"],
                         padx=12, pady=10)
        frame.pack(fill=tk.X)

        tk.Label(frame, text="Ask Anything  💬", bg=_C["card_bg"], fg=_C["header"],
                 font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 6))

        inp_row = tk.Frame(frame, bg=_C["card_bg"])
        inp_row.pack(fill=tk.X)

        self._input_var = tk.StringVar()
        self._entry = tk.Entry(
            inp_row, textvariable=self._input_var,
            font=("Segoe UI", 11), state=tk.DISABLED,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=_C["border"],
            bg="#f8fafc",
        )
        self._entry.pack(fill=tk.X, expand=True, side=tk.LEFT,
                         padx=(0, 8), ipady=7)
        self._entry.bind("<Return>", lambda _e: self._submit())

        self._send_btn = tk.Button(
            inp_row, text="  Send  ➤",
            font=("Segoe UI", 10, "bold"),
            bg=_C["accent"], fg="white",
            activebackground=_C["accent_dk"],
            relief=tk.FLAT, padx=14, pady=7, cursor="hand2",
            command=self._submit, state=tk.DISABLED,
        )
        self._send_btn.pack(side=tk.LEFT)

        # Action row beneath input
        act = tk.Frame(frame, bg=_C["card_bg"])
        act.pack(fill=tk.X, pady=(8, 0))
        tk.Button(
            act, text="🗑  Clear Output",
            font=("Segoe UI", 9), bg=_C["bg"], fg=_C["muted"],
            activebackground=_C["border"], relief=tk.FLAT,
            padx=8, pady=4, cursor="hand2",
            command=self._clear_output,
        ).pack(side=tk.LEFT)
        tk.Label(
            act,
            text="Tip: ask 'Scorecard for <match_id>' after viewing recent results.",
            bg=_C["card_bg"], fg=_C["muted"],
            font=("Segoe UI", 9, "italic"),
        ).pack(side=tk.RIGHT)

    def _build_output_area(self):
        outer = tk.Frame(self, bg=_C["bg"], padx=18, pady=10)
        outer.pack(fill=tk.BOTH, expand=True)

        tk.Label(outer, text="Response", bg=_C["bg"], fg=_C["header"],
                 font=("Segoe UI", 11, "bold")).pack(anchor=tk.W, pady=(0, 4))

        card = tk.Frame(outer, bg=_C["card_bg"],
                        highlightthickness=1,
                        highlightbackground=_C["border"])
        card.pack(fill=tk.BOTH, expand=True)

        self._output = scrolledtext.ScrolledText(
            card, wrap=tk.WORD,
            font=("Consolas", 11),
            bg=_C["card_bg"], fg=_C["text"],
            relief=tk.FLAT, padx=12, pady=10,
            height=18,
        )
        self._output.pack(fill=tk.BOTH, expand=True)

        # Tag for tool-call annotation lines
        self._output.tag_configure(
            "tool_tag",
            foreground=_C["tool_fg"],
            background=_C["tool_bg"],
            font=("Consolas", 9, "italic"),
        )
        self._output.tag_configure(
            "section",
            foreground=_C["header"],
            font=("Segoe UI", 10, "bold"),
        )
        self._output.config(state=tk.DISABLED)

    def _build_status_bar(self):
        self._status_var = tk.StringVar(value="Starting…")
        tk.Label(
            self, textvariable=self._status_var,
            anchor=tk.W,
            bg=_C["status_bg"], fg=_C["status_fg"],
            font=("Segoe UI", 9),
            padx=14, pady=5,
        ).pack(fill=tk.X, side=tk.BOTTOM)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _set_status(self, text: str):
        self._status_var.set(text)

    def _set_controls(self, enabled: bool):
        state = tk.NORMAL if enabled else tk.DISABLED
        self._entry.config(state=state)
        self._send_btn.config(state=state)
        for btn in self._quick_buttons:
            btn.config(state=state)
        if enabled:
            self._entry.focus_set()

    def _set_loading(self, loading: bool):
        self._loading = loading
        if loading:
            self._set_controls(False)
            self._set_status("Thinking… calling tools and preparing the answer.")
            self._send_btn.config(text="Wait…")
        else:
            self._set_controls(True)
            self._send_btn.config(text="  Send  ➤")
            self._set_status("Ready — ask another IPL 2026 question.")

    def _append_output(self, text: str, tag: str | None = None):
        self._output.config(state=tk.NORMAL)
        if tag:
            self._output.insert(tk.END, text, tag)
        else:
            self._output.insert(tk.END, text)
        self._output.see(tk.END)
        self._output.config(state=tk.DISABLED)

    def _clear_output(self):
        self._output.config(state=tk.NORMAL)
        self._output.delete("1.0", tk.END)
        self._output.config(state=tk.DISABLED)

    # ── query flow ────────────────────────────────────────────────────────────

    def _submit(self):
        query = self._input_var.get().strip()
        if not query or self._loading or not self._ready:
            return
        self._input_var.set("")
        self._run_query(query)

    def _run_query(self, query: str):
        if self._loading or not self._ready:
            return

        self._set_loading(True)
        self._append_output("\n" + "─" * 72 + "\n", "section")
        self._append_output(f"❓ {query}\n\n")

        async def _async_query():
            async def on_tool(name: str, args: dict, _result: str):
                args_text = f"  {args}" if args else ""
                self.after(
                    0,
                    lambda n=name, a=args_text: self._append_output(
                        f"  ⚙  Tool: {n}{a}\n", "tool_tag"
                    ),
                )

            try:
                answer = await self._agent.chat(query, on_tool_call=on_tool)
                self.after(
                    0,
                    lambda ans=answer: [
                        self._append_output(f"\n{ans}\n"),
                        self._set_loading(False),
                    ],
                )
            except Exception as exc:
                self.after(
                    0,
                    lambda exc=exc: [
                        self._append_output(f"\n❌ Error: {exc}\n"),
                        self._set_loading(False),
                        self._set_status(f"Error: {exc}"),
                    ],
                )

        asyncio.run_coroutine_threadsafe(_async_query(), self._loop)

    def _on_close(self):
        if self._agent:
            asyncio.run_coroutine_threadsafe(self._agent.stop(), self._loop)
        self._loop.call_soon_threadsafe(self._loop.stop)
        self.destroy()


# ─────────────────────────────────────────────────────────────────────────────
# CLI smoke test
# ─────────────────────────────────────────────────────────────────────────────

async def _cli_test():
    agent = IPLAgent()
    print("Connecting to MCP server...", flush=True)
    await agent.start()
    print("Connected. Running test queries...\n", flush=True)

    for query in [
        "Are there any live IPL 2026 matches right now?",
        "Show me the most recent 3 IPL 2026 results.",
        "Tell me about Rohit Sharma.",
    ]:
        print(f"\n{'=' * 60}\n{query}\n{'-' * 60}")

        async def on_tool(name: str, args: dict, result: str):
            preview = result[:100].replace("\n", " ")
            print(f"Tool: {name}({args}) -> {preview}...")

        answer = await agent.chat(query, on_tool_call=on_tool)
        print(f"\n{answer}")

    await agent.stop()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    missing = [n for n in ("OPENAI_API_KEY", "CRICAPI_KEY") if not os.getenv(n)]
    if missing:
        print("\nMissing environment variables. Set them first:\n")
        for name in missing:
            print(f"  PowerShell:  $env:{name} = 'your_key'")
            print(f"  CMD:         set {name}=your_key")
            print(f"  bash:        export {name}=your_key\n")
        sys.exit(1)

    if "--cli" in sys.argv:
        asyncio.run(_cli_test())
        return

    app = IPLApp()
    app.mainloop()


if __name__ == "__main__":
    main()