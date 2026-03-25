from __future__ import annotations

import asyncio
import logging
import sqlite3
import sys

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command

from qa_agent.config import Settings
from qa_agent.graph import build_graph
from qa_agent.mcp_client import build_mcp, get_notion_tools, list_tool_names
from qa_agent.state import QAState


async def _run() -> None:
    ticket_id = sys.argv[1] if len(sys.argv) > 1 else "ENG-123"

    print("Step: loading settings")
    settings = Settings.load()

    print("Step: starting MCP lifecycle")
    mcp = build_mcp(settings.mcp_config_path)
    toolset = mcp.load_tools()

    print("Step: loading Notion MCP tools")
    notion_tools = await get_notion_tools()

    print("Step: building QA graph with checkpointing")
    async with AsyncSqliteSaver.from_conn_string("qa_agent_memory.db") as checkpointer:
        graph = build_graph(llm=None, tools=toolset, checkpointer=checkpointer)

        config = {
            "configurable": {
                "thread_id": ticket_id,
                "notion_tools": notion_tools,
            }
        }

        print("Step: starting graph run")
        init = QAState(
            ticket_id=ticket_id,
            ticket_data={},
            existing_test_cases=None,
            user_decision=None,
            notion_queries=[],
            notion_search_results=[],
            notion_pages=[],
            draft_test_cases=None,
            reviewed_test_cases=None,
            user_feedback=None,
            approved=False,
            want_playwright=None,
            playwright_project_path=None,
            playwright_tests=None,
            published=False,
            messages=[],
        )

        await graph.ainvoke(init, config=config)

        while True:
            snapshot = await graph.aget_state(config)
            if not snapshot.next:
                break

            if snapshot.next == ("review",):
                print("Step: awaiting human review of test cases.")
            elif snapshot.next == ("want_playwright",):
                print("Step: awaiting Playwright decision / project path.")
            else:
                print(f"Step: graph paused at {snapshot.next}, awaiting input.")

            user_input = await asyncio.get_event_loop().run_in_executor(
                None, input, "> "
            )
            await graph.ainvoke(Command(resume=user_input), config=config)

        loaded_tools = ", ".join(list_tool_names(toolset)) or "(none)"
        logging.info("Loaded tools: %s", loaded_tools)

    print("Agent finished.")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.FileHandler("qa_agent.log"),
        ],
    )
    try:
        asyncio.run(_run())
    except Exception:
        logging.exception("Unhandled error in main QA agent run")
        print("Step: agent run failed; see qa_agent.log for technical details.")


if __name__ == "__main__":
    main()
