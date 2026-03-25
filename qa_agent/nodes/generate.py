from __future__ import annotations

import logging
from typing import Any, Dict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from ..memory import load_preferences
from ..state import QAState as QAAgentState

logger = logging.getLogger(__name__)


def generate_test_cases_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Use Claude to generate structured test cases for the ticket using Notion context.
    """
    logger.info("Generating test cases with Claude...")
    ticket = state.get("ticket_data") or {}
    description = ticket.get("description") or ""
    acceptance = ticket.get("acceptanceCriteria") or ticket.get("acceptance_criteria") or ""
    comments = ticket.get("comments") or []

    comments_text = ""
    if isinstance(comments, list):
        bodies = []
        for c in comments:
            if isinstance(c, dict):
                bodies.append(str(c.get("body") or ""))
        comments_text = "\n\n".join(bodies)

    pages = state.get("notion_pages") or []
    notion_blocks = []
    for p in pages:
        if not isinstance(p, dict):
            continue
        title = p.get("title") or ""
        content = p.get("content") or ""
        notion_blocks.append(f"# {title}\n{content}")
    notion_context = "\n\n".join(notion_blocks)

    existing_cases = state.get("existing_test_cases") or ""
    user_decision = (state.get("user_decision") or "").lower()

    supplement_instructions = ""
    if user_decision == "supplement" and existing_cases:
        supplement_instructions = (
            "Existing test cases are provided below. You MUST add new test cases that\n"
            "do not duplicate or trivially rephrase these. Focus on genuinely new\n"
            "coverage and edge cases.\n\n"
            "Existing test cases:\n"
            f"{existing_cases}\n\n"
        )

    preferences = load_preferences()
    prefs_block = ""
    if preferences:
        joined_prefs = "\n".join(f"- {p}" for p in preferences)
        prefs_block = (
            "User preferences from past feedback (you MUST respect these):\n"
            f"{joined_prefs}\n\n"
        )

    prompt = (
        "You are a senior QA engineer generating high-quality, detailed test cases.\n\n"
        "Ticket description:\n"
        f"{description}\n\n"
        "Acceptance criteria (if any):\n"
        f"{acceptance}\n\n"
        "Relevant comments from the ticket:\n"
        f"{comments_text}\n\n"
        "Relevant Notion pages (specs, designs, prior test docs):\n"
        f"{notion_context}\n\n"
        f"{prefs_block}"
        f"{supplement_instructions}"
        "Generate between 5 and 15 test cases that thoroughly cover functional paths,\n"
        "edge cases, error handling, and important UX expectations.\n\n"
        "Format your response EXACTLY like this pattern, with sequential IDs:\n"
        "### TC-001: <Title>\n"
        "- **Type:** <functional / regression / edge / exploratory / etc.>\n"
        "- **Priority:** <P0/P1/P2/etc.>\n"
        "- **Preconditions:** <bullet-style description>\n"
        "- **Steps:** <numbered or bulleted steps, clear and executable>\n"
        "- **Expected Result:** <precise, observable outcome>\n\n"
        "Continue with TC-002, TC-003, etc. Use Markdown exactly as shown."
    )

    llm = ChatAnthropic(model="claude-sonnet-4-6")
    resp = llm.invoke([HumanMessage(content=prompt)])
    content = getattr(resp, "content", str(resp))

    print("\n=== DRAFT TEST CASES ===\n")
    print(content)
    print("\n========================\n")

    return {"draft_test_cases": content}


def self_review_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Ask Claude to critically self-review and refine the draft test cases.
    """
    logger.info("Self-reviewing test cases with Claude...")
    draft = state.get("draft_test_cases") or ""

    prompt = (
        "You are a meticulous QA lead reviewing a set of proposed test cases.\n\n"
        "Here are the draft test cases:\n\n"
        f"{draft}\n\n"
        "Carefully audit these test cases for the following:\n"
        "- Duplicate or overlapping cases: explicitly flag and merge/remove them.\n"
        "- Vague steps: rewrite them to be concrete and executable.\n"
        "- Missing edge cases suggested by the acceptance criteria or context.\n"
        "- Incorrect or inconsistent priority assignments.\n"
        "- Gaps in coverage (important scenarios that are not tested).\n\n"
        "Then produce a cleaned-up, final set of test cases in the SAME FORMAT\n"
        "as the original (### TC-001, TC-002, etc.), with consistent numbering\n"
        "and no commentary outside the test cases themselves."
    )

    llm = ChatAnthropic(model="claude-sonnet-4-6")
    resp = llm.invoke([HumanMessage(content=prompt)])
    content = getattr(resp, "content", str(resp))

    print("\n=== REVIEWED TEST CASES ===\n")
    print(content)
    print("\n===========================\n")

    return {"reviewed_test_cases": content}
