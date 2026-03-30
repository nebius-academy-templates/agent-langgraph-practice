from __future__ import annotations

from typing import Dict

from langchain_core.messages import HumanMessage

from ..state import QAState as QAAgentState
from ..tools.linear import _fetch_issue


def extract_node(state: QAAgentState) -> Dict:
    """
    Fetch the Linear ticket and detect any existing test cases.

    TODO:
    - Read state["ticket_id"].
    - Call _fetch_issue(ticket_id) to get the ticket data dict.
    - Scan the comments list for any comment whose body contains "TC-001" or
      "### TC-" — these are previously generated test cases.
    - Return {"ticket_data": <dict>, "existing_test_cases": <str | None>}
      where existing_test_cases is the body of the first matching comment, or None.
    """
    raise NotImplementedError("TODO: implement extract_node")


def check_existing_node(state: QAAgentState) -> Dict:
    """
    If existing test cases were found, ask the user what to do next.

    TODO:
    - Read state.get("existing_test_cases").
    - If None or empty, return {} (nothing to do).
    - Otherwise return {"messages": [HumanMessage(content=<prompt>)]} where the
      prompt asks the user to reply "replace", "supplement", or "skip".
    """
    raise NotImplementedError("TODO: implement check_existing_node")
