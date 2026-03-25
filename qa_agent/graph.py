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
    approved = bool(state.get("approved"))
    return "approved" if approved else "needs_changes"


def build_graph(
    *,
    llm: Optional[object] = None,
    tools: Optional[MCPToolset] = None,
    checkpointer: Optional[object] = None,
):
    """
    Build a LangGraph QA graph.

    `llm` and `tools` are dependency-injected to keep nodes import-light.
    """
    g = StateGraph(QAState)

    g.add_node("extract", extract_node)
    g.add_node("check_existing", check_existing_node)
    g.add_node("notion_search", search_notion_node)
    g.add_node("notion_enrich", enrich_notion_node)
    g.add_node("generate", generate_test_cases_node)
    g.add_node("self_review", self_review_node)
    g.add_node("review", review_node)
    g.add_node("want_playwright", want_playwright_node)
    g.add_node("generate_playwright", generate_playwright_node)
    g.add_node("publish", publish_node)

    g.add_edge(START, "extract")
    g.add_edge("extract", "check_existing")
    g.add_edge("check_existing", "notion_search")
    g.add_edge("notion_search", "notion_enrich")
    g.add_edge("notion_enrich", "generate")
    g.add_edge("generate", "self_review")
    g.add_edge("self_review", "review")

    # After human review, either proceed to the Playwright decision node
    # or route back to regeneration with feedback.
    g.add_conditional_edges(
        "review",
        _route_after_review,
        {
            "approved": "want_playwright",
            "needs_changes": "generate",
        },
    )

    g.add_edge("want_playwright", "generate_playwright")
    g.add_edge("generate_playwright", "publish")
    g.add_edge("publish", END)

    compile_kwargs = {"interrupt_before": ["review", "want_playwright"]}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer

    return g.compile(**compile_kwargs)
