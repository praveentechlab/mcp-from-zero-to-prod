# Smart Student Assistant — Multi-Server MCP Demo

A complete **multi-server MCP agent** using **Streamable HTTP** transport, **OpenAI** for intent detection and reasoning, and a **Tkinter desktop UI** for live demonstrations.

The project shows how one AI agent can coordinate tools from three independent MCP servers — Calendar, Notes, and Quiz — without hardcoding any student data or business logic inside the agent itself.

---

## Demo Scenario

A student asks:

```text
Help me prepare for my AI exam tomorrow.
```

The agent does not answer from static data. It calls the right MCP servers based on OpenAI's intent plan and composes a structured final response:

| MCP Server | Port | Tools |
| --- | ---: | --- |
| Calendar MCP Server | `8101` | `get_upcoming_events` |
| Notes MCP Server | `8102` | `list_notes`, `read_note` |
| Practice Quiz MCP Server | `8103` | `generate_quiz`, `get_revision_tip` |

All three servers expose tools over **Streamable HTTP** at `/mcp`.

---

## What This Demo Teaches

- How one agent connects to **multiple MCP servers simultaneously** using `AsyncExitStack`
- How **Streamable HTTP** transport differs from a single stdio server
- How **OpenAI detects query intent** and returns a JSON routing plan
- How tools are **separated by responsibility** across independent servers
- How local markdown files become useful context through an MCP server
- How to run a **Tkinter desktop UI** alongside an async MCP agent using threads

---

## How It Works

```text
Student query
  → Step 0:  OpenAI detects intent → JSON routing plan
  → Step 1:  Calendar MCP Server  → exam details
  → Step 2-3: Notes MCP Server   → list + read matching notes
  → Step 4:  OpenAI               → creates study plan from context
  → Step 5:  Quiz MCP Server      → generates practice questions
  → Final:   OpenAI               → composes full structured response
```

### Intent Routing

OpenAI returns a JSON plan that tells the agent exactly which servers to call:

```json
{
  "intent": "full_preparation",
  "needs_calendar": true,
  "needs_notes": true,
  "needs_plan": true,
  "needs_quiz": true,
  "topic_query": "AI exam preparation",
  "available_hours": 4,
  "quiz_count": 5
}
```

The agent calls only the servers flagged as `true`. Different queries produce different flows:

| Query | Servers Called |
| --- | --- |
| `What exams are coming up?` | Calendar |
| `What are the important AI topics from my notes?` | Notes |
| `Give me a quiz on search algorithms.` | Notes, Quiz |
| `Create a 4-hour study plan for my AI midterm.` | Calendar, Notes → OpenAI plan |
| `Help me prepare for my AI exam tomorrow.` | Calendar, Notes, Quiz → OpenAI plan |

---

## Project Structure

```text
smart_student_assistant_mcp/
  agent_client.py          ← coordinator + Tkinter desktop UI
  calendar_server.py       ← Calendar MCP Server (port 8101)
  notes_server.py          ← Notes MCP Server (port 8102)
  quiz_server.py           ← Practice Quiz MCP Server (port 8103)
  requirements.txt
  .env.example
  README.md
  CALENDAR_SERVER_README.md
  NOTES_SERVER_README.md
  QUIZ_SERVER_README.md
  demo_script.md
  notes/
    ai_intro.md
    neural_networks.md
    search_algorithms.md
```

---

## Setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 2. Install dependencies

```powershell
pip install -r requirements.txt
```

`requirements.txt` contains:

```text
mcp[cli]>=1.9.0
openai>=1.99.0
python-dotenv>=1.0.0
```

### 3. Configure OpenAI

Create a `.env` file from the example:

```powershell
copy .env.example .env
```

Edit `.env` and set your values:

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

> **Important:** `OPENAI_API_KEY` is required. The agent always uses OpenAI for intent detection and final response composition. If the key is missing the agent shows a clear configuration error before starting any servers.

---

## Running the Demo

### CLI mode (single command — starts all servers automatically)

```powershell
python agent_client.py
```

### CLI mode with a custom question

```powershell
python agent_client.py "I have an AI exam tomorrow. Make a study plan."
python agent_client.py "What exams are coming up?"
python agent_client.py "Give me a quiz on search algorithms."
```

### Tkinter desktop UI

```powershell
python agent_client.py --ui
```

The UI includes:
- **Three server cards** — Calendar (blue), Notes (green), Quiz (purple)
- **Question input box** with a Run Demo button
- **Live colour-coded output panel** — each step, topic, and quiz question appears in a different colour as the demo runs
- **Status bar** showing the current agent action

> The agent starts all three MCP servers automatically when you run it. You do not need to launch them separately.

---

## Running Servers Manually

If you want to start the servers individually, open three separate terminals:

**Terminal 1 — Calendar server**
```powershell
python calendar_server.py
```

**Terminal 2 — Notes server**
```powershell
python notes_server.py
```

**Terminal 3 — Quiz server**
```powershell
python quiz_server.py
```

The MCP endpoints will be available at:

```text
http://127.0.0.1:8101/mcp   Calendar MCP Server
http://127.0.0.1:8102/mcp   Notes MCP Server
http://127.0.0.1:8103/mcp   Practice Quiz MCP Server
```

---

## Sample Queries

### Full Preparation

```text
Help me prepare for my AI exam tomorrow.
I have an AI exam tomorrow. Find my notes and create a study plan.
Check my upcoming exams and help me revise AI topics.
Prepare me for tomorrow's AI Midterm Exam.
```

### Calendar

```text
What exams are coming up?
Do I have any exam tomorrow?
Show my upcoming academic events.
```

### Notes

```text
Find my AI notes and suggest what I should study first.
What are the important AI topics from my notes?
Summarize my AI notes.
Help me revise search algorithms for my AI exam.
```

### Study Plan

```text
Create a 4-hour study plan for my AI midterm.
Do I have any exam coming up? If yes, prepare a revision plan.
Summarize my AI notes and plan my study schedule.
```

### Quiz

```text
Give me a quiz on search algorithms.
Create three practice questions from my AI notes.
Test me on neural networks.
Generate a quick revision quiz for my AI exam.
```

---

## Expected CLI Output

```text
SMART STUDENT ASSISTANT - MULTI-SERVER MCP DEMO
==============================================================
Student question: Help me prepare for my AI exam tomorrow.

0) Agent asks OpenAI LLM to understand the query intent...
   Intent: full_preparation (OpenAI model: gpt-4o-mini)
   Reason: The student wants comprehensive preparation...

1) Agent asks Calendar MCP Server for upcoming events...
   Found event: AI Midterm Exam at 2026-05-01T10:00 in Room C-204

2) Agent asks Notes MCP Server for notes matching 'AI exam preparation'...
   Notes found:
   - ai_intro.md: AI Introduction
   - neural_networks.md: Neural Networks Basics
   - search_algorithms.md: AI Search Algorithms

3) Agent reads selected notes and extracts matching topics...
   - Definition of Artificial Intelligence
   - Difference between AI, Machine Learning, and Deep Learning
   - Intelligent agents and their environments
   - Problem-solving agents
   - Evaluation using rationality and performance measures
   - Perceptron model

4) Agent keeps study-plan generation for OpenAI reasoning...
   OpenAI will create a 4.0-hour plan from Calendar + Notes context.

5) Agent asks Practice Quiz MCP Server for 5 question(s)...
   Q1. Explain this topic in two or three sentences: Definition of AI
   ...

Final) Agent asks OpenAI LLM to compose an intent-specific answer...

FINAL ASSISTANT RESPONSE
==============================================================
Your next exam is AI Midterm Exam on 2026-05-01 at 10:00 in Room C-204.
...
```

---

## Architecture

```text
The agent coordinates.
Calendar data comes from the Calendar MCP Server.
Study notes come from the Notes MCP Server.
Study-plan reasoning comes from OpenAI.
Practice questions come from the Quiz MCP Server.
Streamable HTTP lets all servers run independently and still work together.
```

### Key Design Decisions

| Decision | Reason |
| --- | --- |
| `SERVERS` list as single source of truth | Add a server by adding one dictionary — zero other changes |
| OpenAI intent detection before server startup | Catches bad API keys immediately, before any subprocess is launched |
| `AsyncExitStack` for all three sessions | Manages multiple MCP connections in a loop — clean and extensible |
| `finally` block always stops servers | No orphaned processes regardless of success or failure |
| Worker thread + `queue.Queue` | Tkinter UI stays fully responsive while the async demo runs |

---

## Extension Ideas

| Extension | What to change |
| --- | --- |
| Real Google Calendar | Replace `calendar_server.py` with a Google Calendar MCP server |
| Notion or OneDrive notes | Replace the `notes/` folder with a Notion or OneDrive MCP server |
| Email notification | Add a notification MCP server that emails the final study plan |
| Weather-aware suggestions | Add a weather server to suggest study location based on forecast |
| Multi-student support | Add authentication so each student gets their own notes and schedule |

---

## Why This Is a Good Classroom Demo

- The domain (exam prep) is immediately relatable to any student
- Each file is small enough to explain line by line
- Each server has one clear, testable responsibility
- The client demonstrates real multi-server MCP orchestration
- The Tkinter UI makes the multi-step flow visually obvious in real time
- The project can be upgraded incrementally — replace one server at a time

---

*PraveenTechlab · MCP Series · Episode 5*
