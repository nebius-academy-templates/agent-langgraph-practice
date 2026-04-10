In this task, you'll implement a LangGraph-based QA agent that fetches a Linear ticket, enriches it with Notion context via MCP, generates test cases with Claude, walks through a human-in-the-loop review, and publishes the final output back to Linear.

You'll configure credentials, implement the Linear tools and graph nodes, wire the LangGraph workflow, and run the full agent end to end.

👩‍💻 Workflow at a glance
1. Set up your environment 
2. Configure credentials
3. Implement the Linear tools
4. Implement the nodes
5. Wire the graph
6. Run the agent
7. Validate locally
8. Submit your task

Let's go!

## 1. Set up your environment

Once you log in to your GitHub account, the repository for this task will be added automatically.

1. Confirm that `agent-langgraph-practice` appears in your GitHub account.
2. Clone the repo and open it in your editor.
3. Make sure you have Python 3.11+ and Node.js installed.

Install dependencies:

```
# with uv (recommended)
uv pip install -e .

# or with pip
pip install -e .
```

### Repository layout

```
qa-langgraph-agent-reference/
├── qa_agent/
│   ├── config.py               ← provided: settings loaded from .env
│   ├── graph.py                ← TODO: wire the StateGraph (Task 5)
│   ├── mcp_client.py           ← provided: Notion MCP tool loader
│   ├── memory.py               ← provided: in-session preference store
│   ├── state.py                ← provided: QAState TypedDict
│   ├── nodes/
│   │   ├── extract.py          ← TODO: fetch ticket, detect existing cases (Task 4.1)
│   │   ├── generate.py         ← TODO: generate + self-review test cases (Task 4.2)
│   │   ├── notion.py           ← TODO: search and enrich Notion context (Task 4.3)
│   │   ├── review.py           ← TODO: human-in-the-loop interrupt (Task 4.4)
│   │   └── playwright.py       ← TODO: Playwright generation + publish (Task 4.5)
│   └── tools/
│       └── linear.py           ← TODO: _fetch_issue, get_linear_ticket, post_linear_comment (Task 3)
├── mcp_config.json             ← edit: add your Notion API key (Task 2.2)
├── main.py                     ← provided: runnable entrypoint
├── pyproject.toml
└── .env                        ← create: add API keys (Task 2.1)
```

## 2. Configure credentials

### 2.1. Create `.env`

Create a `.env` file in the project root:

```
LINEAR_API_KEY=lin_api_your_key_here
NOTION_API_KEY=ntn_your_key_here
ANTHROPIC_API_KEY=sk-ant-your_key_here
LANGCHAIN_API_KEY=lsv2_your_key_here
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGCHAIN_PROJECT=qa-langgraph-agent
```

**Where to get each key:**

- `LINEAR_API_KEY`: Linear → Settings → API → Personal API keys
- `NOTION_API_KEY`: Notion → Settings → Connections → Develop or manage integrations
- `ANTHROPIC_API_KEY`: console.anthropic.com → API keys
- `LANGCHAIN_API_KEY`: smith.langchain.com → Settings → API keys

### 2.2. Configure `mcp_config.json`

Replace the `<NOTION_API_KEY>` placeholder in `mcp_config.json` with your real Notion key:

```
{
  "notion": {
    "transport":"stdio",
    "command":"npx",
    "args": ["-y","@notionhq/notion-mcp-server"],
    "env": {
      "OPENAPI_MCP_HEADERS":"{\"Authorization\": \"Bearer ntn_your_key_here\", \"Notion-Version\": \"2022-06-28\"}"
    }
  }
}
```

## 3. Implement the Linear tools

Implement the required functions in `qa_agent/tools/linear.py`.

The file already provides `_get_api_key()` and `_graphql()` helpers.

### Requirements

| **Function** | **What it does** |
| --- | --- |
| `_fetch_issue(ticket_id)` | Runs the provided GraphQL query, normalises labels/comments to flat lists, returns a dict |
| `get_linear_ticket(ticket_id)` | `@tool` wrapper — calls `_fetch_issue` and returns the result |
| `list_linear_comments(ticket_id)` | `@tool` wrapper — returns `issue.get("comments", [])` |
| `post_linear_comment(ticket_id, body)` | `@tool` — resolves UUID via `_fetch_issue`, runs CommentCreate mutation, returns confirmation string |

## 4. Implement the nodes

Each node is a function that receives `QAState` and returns a dict of state updates.

### 4.1. `nodes/extract.py`

Implement:

- `extract_node`: Call `_fetch_issue`, scan comments for `"TC-001"` or `"### TC-"` patterns, return `ticket_data` and `existing_test_cases`.
- `check_existing_node`: If existing test cases are found, return a `HumanMessage` prompting the user to choose `"replace"`, `"supplement"`, or `"skip"`.

### 4.2. `nodes/generate.py`

Implement:

- `generate_test_cases_node`: Build a prompt from ticket data, Notion pages, and user preferences (`load_preferences()`), call `ChatAnthropic(model="claude-sonnet-4-6")`, return `draft_test_cases`.
    
    Format: `### TC-001: <Title>` with Type, Priority, Preconditions, Steps, Expected Result.
    
- `self_review_node`: Prompt Claude (as a QA lead) to audit the draft for duplicates, vague steps, and gaps; return `reviewed_test_cases` in the same format.

### 4.3. `nodes/notion.py`

Implement:

- `search_notion_node`: Get Notion tools from `config["configurable"]["notion_tools"]`, ask Claude to pick 2–4 search queries, call the tools, collect unique results, and return `notion_search_results`.
- `enrich_notion_node`: For each search result, call the fetch-page tool with `page_id`, normalise to `{id, title, content}`, return `notion_pages`.

### 4.4. `nodes/review.py`

Implement:

- `review_node`: Print the reviewed test cases, call `interrupt("awaiting_review")` to pause for human input, parse the response (`"approve"` / `"ok"` / `""` → approved, anything else → feedback), call `remember_feedback` if feedback is present, and return `approved`, `user_feedback`, and conversation messages.

### 4.5. `nodes/playwright.py`

Implement:

- `want_playwright_node`: Call `interrupt({...})` to ask the user yes/no for Playwright tests; if yes, call `interrupt` again for the project path; return `want_playwright` and `playwright_project_path`.
- `generate_playwright_node`: If `want_playwright` is `True`, prompt Claude to generate TypeScript Playwright tests from the reviewed cases; return `playwright_tests`.
- `publish_node`: Build a comment body from `reviewed_test_cases` (append Playwright code block if `want_playwright`), call `post_linear_comment(ticket_id, body)`, return `{"published": True}`.

## 5. Wire the graph

Implement `build_graph` in `qa_agent/graph.py` using `StateGraph(QAState)`.

### Required graph flow

```
START → extract → check_existing → notion_search → notion_enrich
      → generate → self_review → review
                                   ↓ (conditional)
                    approved → want_playwright → generate_playwright → publish → END
                    needs_changes → generate  (loop back)
```

Compile with `interrupt_before=["review", "want_playwright"]`.

Pass the checkpointer to `compile()` if it is not `None`.

## 6. Run the agent

Run:

```
python main.py #3
```

Replace `ENG-123` with a real ticket ID from your Linear workspace or from [this repository](https://github.com/nebius-academy-templates/issue-examples/issues).

At the review pause, type `approve` to accept or describe a change.

At the `want_playwright` pause, type `yes` or `no`.

### Tips

- LangGraph state is persisted between interrupts via SQLite (`qa_agent_memory.db`). Delete this file to start a fresh run.
- Logs are written to `qa_agent.log` — check it if a run fails silently.
- If Notion MCP tools fail to load, make sure [Node.js](https://nodejs.org) is installed.
- User feedback with phrases like `"avoid duplicates"` or `"fewer test cases"` is remembered by `memory.py` and applied in future generate calls within the same session.
- LangSmith tracing is enabled automatically via the `LANGCHAIN_*` env variables. After a run, open `smith.langchain.com` to see the full trace of every node and LLM call.

## 8. Submit your task

Before submitting, review the checklist.

### ✅ Submission checklist

- [ ]  `.env` exists with all seven variables set to real values
- [ ]  `mcp_config.json` has the Notion server configured
- [ ]  `qa_agent/tools/linear.py` — `_fetch_issue`, `get_linear_ticket`, `post_linear_comment` implemented
- [ ]  `qa_agent/nodes/extract.py` — `extract_node` and `check_existing_node` implemented
- [ ]  `qa_agent/nodes/generate.py` — `generate_test_cases_node` and `self_review_node` implemented
- [ ]  `qa_agent/nodes/notion.py` — `search_notion_node` and `enrich_notion_node` implemented
- [ ]  `qa_agent/nodes/review.py` — `review_node` with `interrupt()` implemented
- [ ]  `qa_agent/nodes/playwright.py` — `want_playwright_node`, `generate_playwright_node`, `publish_node` implemented
- [ ]  `qa_agent/graph.py` — `build_graph` wires all nodes with correct edges and interrupts
- [ ]  `python main.py <ticket-id>` runs end-to-end without errors
- [ ]  Human review loop works: pause → feedback → regenerate → approve
- [ ]  The agent publishes test cases to the Linear ticket after approval
- [ ]  All `verify.py` checks pass
- [ ]  Changes are committed and pushed to `main`

1. Commit your changes.
2. Push to GitHub.
3. Return to the lesson and click "Submit."
