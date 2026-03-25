from __future__ import annotations

from typing import Dict

from langchain_core.messages import HumanMessage

from ..state import QAState as QAAgentState
from ..tools.linear import _fetch_issue


def extract_node(state: QAAgentState) -> Dict:
    """
    Fetch the Linear ticket and detect any existing test cases.
    """
    ticket_id = state["ticket_id"]

    ticket_data = _fetch_issue(ticket_id)
    comments = ticket_data.get("comments", [])

    existing_test_cases: str | None = None
    for c in comments:
        body = (c.get("body") or "") if isinstance(c, dict) else ""
        if "TC-001" in body or "### TC-" in body:
            existing_test_cases = body
            break

    return {
        "ticket_data": ticket_data,
        "existing_test_cases": existing_test_cases,
    }


def check_existing_node(state: QAAgentState) -> Dict:
    """
    If existing test cases were found, ask the user what to do next.
    """
    existing = state.get("existing_test_cases")
    if not existing:
        return {}

    prompt = (
        "I found existing test cases on this Linear ticket.\n\n"
        "What would you like to do?\n"
        '- reply **"replace"** to overwrite them\n'
        '- reply **"supplement"** to add additional cases\n'
        '- reply **"skip"** to leave them unchanged\n'
    )
    return {"messages": [HumanMessage(content=prompt)]}
