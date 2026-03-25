from __future__ import annotations

import os
from typing import Any, Dict, List

import httpx
from langchain_core.tools import tool

LINEAR_API_URL = "https://api.linear.app/graphql"


def _get_api_key() -> str:
    key = os.environ.get("LINEAR_API_KEY")  # usually set by config.load_dotenv()
    if not key:
        # Allow using these tools standalone (without first calling Settings.load()).
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
        "Authorization": _get_api_key(),  # raw key, no Bearer prefix
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

    data = _graphql(query, {"id": ticket_id})
    issue = data.get("issue")
    if not issue:
        return {}

    labels_nodes = (issue.get("labels") or {}).get("nodes") or []
    comments_nodes = (issue.get("comments") or {}).get("nodes") or []

    labels: List[str] = [n.get("name", "") for n in labels_nodes if n.get("name")]
    comments: List[Dict[str, Any]] = []
    for c in comments_nodes:
        comments.append(
            {
                "id": c.get("id"),
                "body": c.get("body") or "",
                "createdAt": c.get("createdAt"),
                "author": (c.get("user") or {}).get("name"),
            }
        )

    state = issue.get("state") or {}
    state_str = state.get("name") or state.get("type")

    return {
        "id": issue.get("id"),
        "identifier": issue.get("identifier"),
        "title": issue.get("title") or "",
        "description": issue.get("description") or "",
        "priority": issue.get("priority"),
        "priorityLabel": issue.get("priorityLabel"),
        "state": state_str,
        "labels": labels,
        "comments": comments,
    }


@tool
def get_linear_ticket(ticket_id: str) -> Dict[str, Any]:
    """
    Fetch a Linear ticket by identifier or internal ID and return a normalised issue dict.
    """

    return _fetch_issue(ticket_id)


@tool
def list_linear_comments(ticket_id: str) -> List[Dict[str, Any]]:
    """
    List comments on a Linear ticket. Returns an empty list if the issue is not found.
    """

    issue = _fetch_issue(ticket_id)
    return issue.get("comments", []) if issue else []


@tool
def post_linear_comment(ticket_id: str, body: str) -> str:
    """
    Post a new comment to a Linear ticket. Accepts either identifier (e.g. 'ENG-123')
    or internal UUID and returns a confirmation string on success.
    """

    issue = _fetch_issue(ticket_id)
    if not issue:
        raise RuntimeError(f"Linear issue not found for '{ticket_id}'.")

    issue_id = issue.get("id")
    if not issue_id:
        raise RuntimeError("Resolved Linear issue is missing an 'id' field.")

    mutation = """
    mutation CommentCreate($input: CommentCreateInput!) {
      commentCreate(input: $input) {
        success
        comment {
          id
        }
      }
    }
    """
    variables = {"input": {"issueId": issue_id, "body": body}}

    data = _graphql(mutation, variables)
    result = (data.get("commentCreate") or {})
    if not result.get("success"):
        raise RuntimeError(f"Failed to create Linear comment: {result}")

    comment = result.get("comment") or {}
    return f"Comment {comment.get('id')} created on issue {issue.get('identifier')}."


__all__ = [
    "_graphql",
    "_fetch_issue",
    "get_linear_ticket",
    "list_linear_comments",
    "post_linear_comment",
]
