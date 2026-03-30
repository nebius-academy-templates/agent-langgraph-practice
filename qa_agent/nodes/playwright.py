from __future__ import annotations

from typing import Any, Dict

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from ..state import QAState as QAAgentState
from ..tools.linear import post_linear_comment


def want_playwright_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Ask the user whether they want Playwright tests generated, and where.

    TODO:
    - Call interrupt({...}) with a message asking "Do you want Playwright tests?  (yes/no)".
      The interrupt payload should also include the reviewed test cases for context.
    - Parse the response: "y" or "yes" → want=True, anything else → want=False.
    - If want is True, call interrupt again asking for the Playwright project path
      (default: "tests" if the user presses Enter without typing).
    - Return {
          "want_playwright": <bool>,
          "playwright_project_path": <str | None>,
          "messages": [AIMessage(...), HumanMessage(...), ...],
      }
    """
    raise NotImplementedError("TODO: implement want_playwright_node")


def generate_playwright_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Generate Playwright tests from the reviewed test cases using Claude.

    TODO:
    - If state["want_playwright"] is False, return {} (skip).
    - Read state["reviewed_test_cases"] and state["playwright_project_path"].
    - Build a prompt asking Claude to generate TypeScript Playwright tests, one per TC-XXX
      case, targeting the project at playwright_project_path.
    - Call ChatAnthropic(model="claude-sonnet-4-6").invoke([AIMessage(content=prompt)]).
    - Return {"playwright_tests": <generated code string>}.
    """
    raise NotImplementedError("TODO: implement generate_playwright_node")


def publish_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Publish the final test cases (and Playwright tests, if any) back to Linear.

    TODO:
    - Read ticket_id, reviewed_test_cases, playwright_tests, want_playwright from state.
    - Build a comment body that includes the reviewed test cases.
    - If want_playwright is True and playwright_tests is not empty, append a fenced
      TypeScript code block with the Playwright tests.
    - Call post_linear_comment(ticket_id, body).
    - Return {"published": True}.
    """
    raise NotImplementedError("TODO: implement publish_node")
