from __future__ import annotations

import logging
from typing import Any, Dict, List

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool
from langgraph.types import RunnableConfig

from ..state import QAState as QAAgentState


def _get_notion_tools_from_config(config: RunnableConfig) -> List[BaseTool]:
    configurable = (config or {}).get("configurable") or {}
    tools = configurable.get("notion_tools") or []
    return list(tools)


async def search_notion_node(
    state: QAAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Use Claude with injected Notion MCP tools to search Notion for relevant pages.

    TODO:
    - Call _get_notion_tools_from_config(config) to get the available Notion tools.
    - If no tools are available, return {} (nothing to do).
    - Build a prompt from state["ticket_data"] (title, description, labels) that
      asks Claude to call the Notion search tool 2-4 times with well-chosen queries.
    - Bind the tools: llm.bind_tools(notion_tools) and invoke with the prompt.
    - Execute each tool_call from the response using tool.ainvoke(args).
    - Collect unique results (deduplicate by "id" or "pageId").
    - Return {"notion_search_results": <list of result dicts>}.
    """
    raise NotImplementedError("TODO: implement search_notion_node")


async def enrich_notion_node(
    state: QAAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Fetch full Notion page contents for the search results.

    TODO:
    - Call _get_notion_tools_from_config(config). If empty, return {}.
    - Find a "fetch" or "page" tool from the list (heuristic: check tool.name).
    - For each item in state["notion_search_results"] (up to 5), extract the page_id
      and call fetch_tool.ainvoke({"page_id": page_id}).
    - Normalise each result to {"id": ..., "title": ..., "content": ...}.
    - Return {"notion_pages": <list of page dicts>}.
    """
    raise NotImplementedError("TODO: implement enrich_notion_node")
