# Practice: LangGraph QA Agent

In this practice you will implement a **LangGraph-based QA agent** that fetches a Linear ticket, enriches it with Notion context via MCP, generates test cases with Claude, walks through a human-in-the-loop review loop, and publishes the final output back to Linear.

---

## Repository layout

```
qa-langgraph-agent-reference/
├── qa_agent/
│   ├── config.py               ← provided: Settings loaded from .env
│   ├── graph.py                ← TODO: wire the StateGraph (Task 4)
│   ├── mcp_client.py           ← provided: Notion MCP tool loader
│   ├── memory.py               ← provided: in-session preference store
│   ├── state.py                ← provided: QAState TypedDict
│   ├── nodes/
│   │   ├── extract.py          ← TODO: fetch ticket, detect existing cases (Task 3a)
│   │   ├── generate.py         ← TODO: generate + self-review test cases (Task 3b)
│   │   ├── notion.py           ← TODO: search and enrich Notion context (Task 3c)
│   │   ├── review.py           ← TODO: human-in-the-loop interrupt (Task 3d)
│   │   └── playwright.py       ← TODO: Playwright generation + publish (Task 3e)
│   └── tools/
│       └── linear.py           ← TODO: _fetch_issue, get_linear_ticket, post_linear_comment (Task 2)
├── mcp_config.json             ← edit: add your Notion API key (Task 1b)
├── main.py                     ← provided: runnable entrypoint
├── pyproject.toml
└── .env                        ← create: add API keys (Task 1a)
```

---

## Step 0 — Install dependencies

Requires Python 3.11+ and Node.js (for the Notion MCP server via `npx`).

```bash
# with uv (recommended)
uv pip install -e .

# or with pip
pip install -e .
```

---

## Task 1 — Configure credentials

### 1a — Create `.env`

Create a `.env` file in the project root:

```bash
LINEAR_API_KEY=lin_api_your_key_here
NOTION_API_KEY=ntn_your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
LANGCHAIN_API_KEY=lsv2_your_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=qa-langgraph-agent
```

Where to get each key:
- **LINEAR_API_KEY**: Linear → Settings → API → Personal API keys
- **NOTION_API_KEY**: Notion → Settings → Connections → Develop or manage integrations
- **ANTHROPIC_API_KEY**: console.anthropic.com → API keys
- **LANGCHAIN_API_KEY**: smith.langchain.com → Settings → API keys

### 1b — Configure `mcp_config.json`

Replace the `<NOTION_API_KEY>` placeholder in `mcp_config.json` with your real Notion key:

```json
{
  "notion": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@notionhq/notion-mcp-server"],
    "env": {
      "OPENAPI_MCP_HEADERS": "{\"Authorization\": \"Bearer ntn_your_key_here\", \"Notion-Version\": \"2022-06-28\"}"
    }
  }
}
```

---

## Task 2 — Implement the Linear tools (`qa_agent/tools/linear.py`)

The file already provides `_get_api_key()` and `_graphql()` helpers. You need to implement:

| Function | What it does |
|---|---|
| `_fetch_issue(ticket_id)` | Runs the provided GraphQL query, normalises labels/comments to flat lists, returns a dict |
| `get_linear_ticket(ticket_id)` | `@tool` wrapper — calls `_fetch_issue` and returns the result |
| `list_linear_comments(ticket_id)` | `@tool` wrapper — returns `issue.get("comments", [])` |
| `post_linear_comment(ticket_id, body)` | `@tool` — resolves UUID via `_fetch_issue`, runs `CommentCreate` mutation, returns confirmation string |

---

## Task 3 — Implement the nodes

Each node is a function that receives `QAState` and returns a `dict` of state updates.

### 3a — `nodes/extract.py`

- **`extract_node`**: call `_fetch_issue`, scan comments for `"TC-001"` or `"### TC-"` pattern, return `ticket_data` and `existing_test_cases`.
- **`check_existing_node`**: if existing test cases found, return a `HumanMessage` prompting the user to choose `"replace"`, `"supplement"`, or `"skip"`.

### 3b — `nodes/generate.py`

- **`generate_test_cases_node`**: build a prompt from ticket data + Notion pages + user preferences (`load_preferences()`), call `ChatAnthropic(model="claude-sonnet-4-6")`, return `draft_test_cases`. Format: `### TC-001: <Title>` with Type, Priority, Preconditions, Steps, Expected Result.
- **`self_review_node`**: build a prompt asking Claude (as a QA lead) to audit the draft for duplicates, vague steps, and gaps; return `reviewed_test_cases` in the same format.

### 3c — `nodes/notion.py`

- **`search_notion_node`**: get Notion tools from `config["configurable"]["notion_tools"]`, ask Claude to pick 2–4 search queries and call the tools, collect unique results, return `notion_search_results`.
- **`enrich_notion_node`**: for each search result, call the fetch-page tool with `page_id`, normalise to `{id, title, content}`, return `notion_pages`.

### 3d — `nodes/review.py`

- **`review_node`**: print the reviewed test cases, call `interrupt("awaiting_review")` to pause for human input, parse the response (`"approve"` / `"ok"` / `""` → approved, anything else → feedback), call `remember_feedback` if feedback is present, return `approved`, `user_feedback`, and conversation messages.

### 3e — `nodes/playwright.py`

- **`want_playwright_node`**: call `interrupt({...})` to ask the user yes/no for Playwright tests; if yes, call `interrupt` again for the project path; return `want_playwright` and `playwright_project_path`.
- **`generate_playwright_node`**: if `want_playwright` is True, prompt Claude to generate TypeScript Playwright tests from the reviewed cases; return `playwright_tests`.
- **`publish_node`**: build a comment body from `reviewed_test_cases` (append Playwright code block if `want_playwright`), call `post_linear_comment(ticket_id, body)`, return `{"published": True}`.

---

## Task 4 — Wire the graph (`qa_agent/graph.py`)

Implement `build_graph` using `StateGraph(QAState)`:

```
START → extract → check_existing → notion_search → notion_enrich
      → generate → self_review → review
                                   ↓ (conditional)
                    approved → want_playwright → generate_playwright → publish → END
                    needs_changes → generate  (loop back)
```

- Compile with `interrupt_before=["review", "want_playwright"]`.
- Pass the `checkpointer` to `compile()` if it is not `None`.

---

## Task 5 — Run the agent

```bash
python main.py ENG-123
```

Replace `ENG-123` with a real ticket ID from your Linear workspace.

At the `review` pause, type `approve` to accept or describe a change. At the `want_playwright` pause, type `yes` or `no`.

---

## Task 6 — Validate

Copy `verify.py` from the solution directory and run it:

```bash
python verify.py
```

All checks must pass before you submit.

---

## Submission checklist

- [ ] `.env` exists with all seven variables set to real values
- [ ] `mcp_config.json` has the Notion server configured
- [ ] `qa_agent/tools/linear.py` — `_fetch_issue`, `get_linear_ticket`, `post_linear_comment` implemented
- [ ] `qa_agent/nodes/extract.py` — `extract_node` and `check_existing_node` implemented
- [ ] `qa_agent/nodes/generate.py` — `generate_test_cases_node` and `self_review_node` implemented
- [ ] `qa_agent/nodes/notion.py` — `search_notion_node` and `enrich_notion_node` implemented
- [ ] `qa_agent/nodes/review.py` — `review_node` with `interrupt()` implemented
- [ ] `qa_agent/nodes/playwright.py` — `want_playwright_node`, `generate_playwright_node`, `publish_node` implemented
- [ ] `qa_agent/graph.py` — `build_graph` wires all nodes with correct edges and interrupts
- [ ] `python main.py <ticket-id>` runs end-to-end without errors
- [ ] Human review loop works: pause → feedback → regenerate → approve
- [ ] Agent publishes test cases to the Linear ticket after approval
- [ ] All `verify.py` checks pass
- [ ] Changes committed and pushed to `main`

---

## Tips

- LangGraph state is persisted between interrupts via SQLite (`qa_agent_memory.db`). Delete this file to start a fresh run.
- Logs go to `qa_agent.log` — check it when a run fails silently.
- If Notion MCP tools fail to load, make sure Node.js is installed: https://nodejs.org
- User feedback containing phrases like "avoid duplicate" or "fewer test cases" is remembered by `memory.py` and applied in future `generate` calls within the same session.
- LangSmith tracing is enabled automatically via the `LANGCHAIN_*` env vars. After a run, open smith.langchain.com to see the full trace of every node and LLM call.
