from __future__ import annotations

from typing import Any, Dict, List

import logging

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
    """
    notion_tools = _get_notion_tools_from_config(config)
    if not notion_tools:
        # No tools injected; nothing to do.
        return {}

    llm = ChatAnthropic(model="claude-sonnet-4-6")
    llm_with_tools = llm.bind_tools(notion_tools)

    ticket = state.get("ticket_data") or {}
    title = ticket.get("title") or ""
    description = ticket.get("description") or ""
    labels = ticket.get("labels") or []
    labels_str = ", ".join(labels) if isinstance(labels, list) else str(labels)

    prompt = (
        "You are helping generate high-quality test cases for a Linear ticket.\n\n"
        f"Title: {title}\n"
        f"Description:\n{description}\n\n"
        f"Labels: {labels_str}\n\n"
        "You have access to Notion search tools.\n"
        "Call the Notion search tool 2-4 times with well-chosen queries that\n"
        "will surface the most relevant existing specs, test documents, or runbooks.\n"
        "After deciding on your queries, respond by calling the tools; do not include\n"
        "a final natural language answer."
    )

    ai_msg = await llm_with_tools.ainvoke([HumanMessage(content=prompt)])
    tool_calls = getattr(ai_msg, "tool_calls", None) or []

    # Execute tool calls and collect results.
    all_results: List[Dict[str, Any]] = []
    seen_ids: set[str] = set()

    for call in tool_calls:
        name = call.get("name")
        args = call.get("args") or {}

        tool: BaseTool | None = next((t for t in notion_tools if t.name == name), None)
        if tool is None:
            continue

        result = await tool.ainvoke(args)

        # Normalise: assume result is a list of page-like dicts.
        if isinstance(result, list):
            items = result
        else:
            items = [result]

        for item in items:
            if not isinstance(item, dict):
                continue
            page_id = str(item.get("id") or item.get("pageId") or "")
            if not page_id or page_id in seen_ids:
                continue
            seen_ids.add(page_id)
            all_results.append(item)

    return {"notion_search_results": all_results}


async def enrich_notion_node(
    state: QAAgentState, config: RunnableConfig
) -> Dict[str, Any]:
    """
    Fetch full Notion page contents for the search results.
    """
    notion_tools = _get_notion_tools_from_config(config)
    if not notion_tools:
        return {}

    # Heuristically pick the fetch-page tool.
    fetch_tool: BaseTool | None = None
    for t in notion_tools:
        name = (t.name or "").lower()
        if "fetch" in name or "page" in name:
            fetch_tool = t
            break

    if fetch_tool is None:
        # No suitable fetch tool available.
        return {}

    logger = logging.getLogger(__name__)

    search_results = state.get("notion_search_results") or []
    if not search_results:
        logger.warning("No Notion search results to enrich.")
        return {}

    pages: List[Dict[str, Any]] = []

    for item in search_results[:5]:
        if not isinstance(item, dict):
            continue
        page_id = item.get("id") or item.get("pageId")
        if not page_id:
            continue

        try:
            result = await fetch_tool.ainvoke({"page_id": page_id})
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to fetch Notion page %s: %s", page_id, exc)
            continue

        if not isinstance(result, dict):
            result = {"raw": result}

        title = result.get("title") or result.get("name") or ""
        content = (
            result.get("content")
            or result.get("markdown")
            or result.get("text")
            or repr(result)
        )

        pages.append({"id": page_id, "title": title, "content": content})

    if not pages:
        logger.warning("No Notion pages could be fetched for search results.")
        return {}

    return {"notion_pages": pages}

