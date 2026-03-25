from __future__ import annotations

from typing import Any, Dict

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import interrupt

from ..memory import remember_feedback
from ..state import QAState as QAAgentState


def review_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Human-in-the-loop review of the generated test cases.
    """
    reviewed = state.get("reviewed_test_cases") or ""

    print("\n=== Reviewed Test Cases ===\n")
    print(reviewed)
    print("\n===========================\n")

    print(
        "\nApprove these test cases? "
        "Type 'approve' (or press Enter) to accept, "
        "or describe what to change:"
    )

    user_input = interrupt("awaiting_review")

    text = (user_input or "").strip()
    normalized = text.lower()

    if normalized in {"", "approve", "ok", "lgtm"}:
        approved = True
        feedback = None
    else:
        approved = False
        feedback = text or None

    if feedback:
        remember_feedback(feedback, state.get("ticket_id"))

    ai_msg = AIMessage(
        content=(
            "Presented the reviewed test cases to the user and asked for "
            "approval or feedback."
        )
    )
    human_msg = HumanMessage(content=text)

    return {
        "approved": approved,
        "user_feedback": feedback,
        "messages": [ai_msg, human_msg],
    }
