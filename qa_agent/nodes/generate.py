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

    TODO:
    - Read ticket_data, notion_pages, existing_test_cases, and user_decision from state.
    - Build a prompt that includes: ticket description, acceptance criteria, comments,
      Notion page content, any user preferences from load_preferences(), and (if
      user_decision == "supplement") instructions not to duplicate existing cases.
    - Call ChatAnthropic(model="claude-sonnet-4-6").invoke([HumanMessage(content=prompt)]).
    - The prompt must instruct Claude to format each test case as:
        ### TC-001: <Title>
        - **Type:** ...
        - **Priority:** ...
        - **Preconditions:** ...
        - **Steps:** ...
        - **Expected Result:** ...
    - Print the result to stdout and return {"draft_test_cases": <content>}.
    """
    raise NotImplementedError("TODO: implement generate_test_cases_node")


def self_review_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Ask Claude to critically self-review and refine the draft test cases.

    TODO:
    - Read state["draft_test_cases"].
    - Build a prompt asking Claude (as a QA lead) to audit the draft for:
        duplicates, vague steps, missing edge cases, priority issues, coverage gaps.
    - Call ChatAnthropic(model="claude-sonnet-4-6").invoke([HumanMessage(content=prompt)]).
    - The prompt must ask Claude to return a cleaned-up set in the same ### TC-XXX format,
      with no commentary outside the test cases.
    - Print the result and return {"reviewed_test_cases": <content>}.
    """
    raise NotImplementedError("TODO: implement self_review_node")
