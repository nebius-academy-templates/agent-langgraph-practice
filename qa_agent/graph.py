from __future__ import annotations

from typing import Optional

from langgraph.graph import END, START, StateGraph

from .mcp_client import MCPToolset
from .nodes.extract import check_existing_node, extract_node
from .nodes.generate import generate_test_cases_node, self_review_node
from .nodes.notion import enrich_notion_node, search_notion_node
from .nodes.playwright import (
    generate_playwright_node,
    publish_node,
    want_playwright_node,
)
from .nodes.review import review_node
from .state import QAState


def _route_after_review(state: QAState) -> str:
    """Router deciding what to do after human review."""
    # TODO: return "approved" if state["approved"] is True, else "needs_changes"
    raise NotImplementedError("TODO: implement _route_after_review")


def build_graph(
    *,
    llm: Optional[object] = None,
    tools: Optional[MCPToolset] = None,
    checkpointer: Optional[object] = None,
):
    """
    Build and compile the LangGraph QA graph.

    TODO — follow these steps:

    1. Create the graph:
           g = StateGraph(QAState)

    2. Register all nodes with g.add_node("name", function):
           extract, check_existing, notion_search, notion_enrich,
           generate, self_review, review, want_playwright,
           generate_playwright, publish

    3. Add linear edges with g.add_edge(source, target):
           START → extract → check_existing → notion_search → notion_enrich
                 → generate → self_review → review

           want_playwright → generate_playwright → publish → END

    4. Add a conditional edge from "review" using _route_after_review:
           "approved"      → "want_playwright"
           "needs_changes" → "generate"

    5. Compile with interrupt_before=["review", "want_playwright"].
       If checkpointer is not None, pass it to compile() as well.

    6. Return the compiled graph.
    """
    raise NotImplementedError("TODO: implement build_graph")
