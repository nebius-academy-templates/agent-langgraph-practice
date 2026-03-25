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
    """
    reviewed = state.get("reviewed_test_cases") or ""

    # First question: do we want Playwright tests at all?
    choice = interrupt(
        {
            "message": (
                "Do you want Playwright tests generated for the approved test cases? "
                "(yes/no)"
            ),
            "test_cases": reviewed,
        }
    )
    choice_text = (choice or "").strip().lower()
    want = choice_text in {"y", "yes"}

    project_path: str | None = None
    msgs: list[Any] = [
        AIMessage(
            content="Asked the user whether they want Playwright tests generated."
        ),
        HumanMessage(content=choice_text),
    ]

    # Second question only if yes.
    if want:
        path = interrupt(
            {
                "message": (
                    "Enter the filesystem path to your Playwright project "
                    '(e.g. "tests" or "apps/web/tests"). Press Enter for the default '
                    '"tests".'
                ),
                "test_cases": reviewed,
            }
        )
        path_text = (path or "").strip()
        project_path = path_text or "tests"
        msgs.append(
            AIMessage(
                content=(
                    "Asked the user for the Playwright project path "
                    "to use when generating tests."
                )
            )
        )
        msgs.append(HumanMessage(content=path_text))

    return {
        "want_playwright": want,
        "playwright_project_path": project_path,
        "messages": msgs,
    }


def generate_playwright_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Generate Playwright tests from the reviewed test cases using Claude.
    """
    if not state.get("want_playwright"):
        return {}

    reviewed = state.get("reviewed_test_cases") or ""
    project_path = state.get("playwright_project_path") or "tests"

    prompt = (
        "You are a senior QA engineer and Playwright expert.\n\n"
        "Below are the final, approved test cases:\n\n"
        f"{reviewed}\n\n"
        f'Generate Playwright test code (TypeScript) suitable for the project at "{project_path}".\n'
        "Focus on clarity, maintainability, and mapping each TC-XXX case to a test.\n"
        "Return only the code, with brief comments where it aids understanding."
    )

    llm = ChatAnthropic(model="claude-sonnet-4-6")
    resp = llm.invoke([AIMessage(content=prompt)])
    content = getattr(resp, "content", str(resp))

    return {"playwright_tests": content}


def publish_node(state: QAAgentState) -> Dict[str, Any]:
    """
    Publish the final test cases (and Playwright tests, if any) back to Linear.
    """
    ticket_id = state.get("ticket_id") or ""
    if not ticket_id:
        return {"published": False}

    body_sections = []

    reviewed = state.get("reviewed_test_cases") or ""
    if reviewed:
        body_sections.append("### Reviewed Test Cases\n\n" + reviewed)

    playwright = state.get("playwright_tests") or ""
    if playwright and state.get("want_playwright"):
        body_sections.append("### Playwright Tests\n\n```ts\n" + playwright + "\n```")

    if not body_sections:
        return {"published": False}

    body = "\n\n---\n\n".join(body_sections)

    confirmation = post_linear_comment(ticket_id, body)

    return {"published": True, "artifacts": [{"linear_comment": confirmation}]}
