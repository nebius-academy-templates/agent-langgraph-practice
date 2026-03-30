from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
from langchain_core.tools import tool

LINEAR_API_URL = "https://api.linear.app/graphql"


def _get_api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            pass
        key = os.environ.get("LINEAR_API_KEY")
    if not key:
        raise RuntimeError("LINEAR_API_KEY is not set in the environment.")
    return key


def _graphql(query: str, variables: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute a GraphQL request against Linear and return the `data` object.
    """
    headers = {
        "Authorization": _get_api_key(),
        "Content-Type": "application/json",
    }
    payload = {"query": query, "variables": variables}

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(LINEAR_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if "errors" in data and data["errors"]:
        raise RuntimeError(f"Linear GraphQL error: {data['errors']}")

    if "data" not in data:
        raise RuntimeError("Linear GraphQL response missing 'data' field.")

    return data["data"]


def _fetch_issue(ticket_id: str) -> Dict[str, Any]:
    """
    Fetch and normalise a Linear issue by identifier or ID.

    Uses the following GraphQL query shape — you can extend the selected fields
    if you need more data (e.g. acceptanceCriteria, assignee, team).

    Returns a normalised dict with keys:
        id, identifier, title, description, priority, priorityLabel,
        state (str), labels (list[str]), comments (list[dict]).
    """
    query = """
    query IssueByIdOrKey($id: String!) {
      issue(id: $id) {
        id
        identifier
        title
        description
        priority
        priorityLabel
        state {
          name
          type
        }
        labels {
          nodes {
            name
          }
        }
        comments {
          nodes {
            id
            body
            createdAt
            user {
              name
            }
          }
        }
      }
    }
    """

    # TODO: call _graphql, extract issue data, and return a normalised dict.
    # Hint: labels are nested under issue["labels"]["nodes"], comments under
    # issue["comments"]["nodes"]. Normalise both to flat lists before returning.
    raise NotImplementedError("TODO: implement _fetch_issue")


@tool
def get_linear_ticket(ticket_id: str) -> Dict[str, Any]:
    """
    Fetch a Linear ticket by identifier or internal ID and return a normalised issue dict.

    TODO: call _fetch_issue(ticket_id) and return the result.
    """
    raise NotImplementedError("TODO: implement get_linear_ticket")


@tool
def list_linear_comments(ticket_id: str) -> List[Dict[str, Any]]:
    """
    List comments on a Linear ticket. Returns an empty list if the issue is not found.

    TODO: call _fetch_issue(ticket_id) and return issue.get("comments", []).
    """
    raise NotImplementedError("TODO: implement list_linear_comments")


@tool
def post_linear_comment(ticket_id: str, body: str) -> str:
    """
    Post a new comment to a Linear ticket.

    Accepts either an identifier (e.g. 'ENG-123') or an internal UUID.
    Returns a confirmation string on success.

    TODO:
    - Call _fetch_issue(ticket_id) to resolve the internal issue UUID.
    - Run a CommentCreate GraphQL mutation using _graphql().
    - Return a confirmation string like "Comment <id> created on issue <identifier>.".

    GraphQL mutation shape:
        mutation CommentCreate($input: CommentCreateInput!) {
          commentCreate(input: $input) {
            success
            comment { id }
          }
        }
    Variables: {"input": {"issueId": <uuid>, "body": <body>}}
    """
    raise NotImplementedError("TODO: implement post_linear_comment")


__all__ = [
    "_graphql",
    "_fetch_issue",
    "get_linear_ticket",
    "list_linear_comments",
    "post_linear_comment",
]
