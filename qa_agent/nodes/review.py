from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from ..memory import remember_feedback
from ..state import QAState as QAAgentState


def review_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Human-in-the-loop review of the generated test cases.

    TODO:
    - Print state["reviewed_test_cases"] to stdout so the user can read them.
    - Call interrupt("awaiting_review") to pause the graph and wait for human input.
      The return value of interrupt() is the user's text response.
    - If the user types "", "approve", "ok", or "lgtm" → set approved=True, feedback=None.
    - Otherwise → set approved=False, feedback=<user text>.
    - If feedback is not None, call remember_feedback(feedback, state["ticket_id"]).
    - Return {
          "approved": <bool>,
          "user_feedback": <str | None>,
          "messages": [AIMessage(...), HumanMessage(...)],
      }
    """
    raise NotImplementedError("TODO: implement review_node")
