from __future__ import annotations

from typing import Any, List, Optional, Tuple

from langgraph.store.memory import InMemoryStore

_store = InMemoryStore()

_PREF_NS = "user_preferences"
_PREF_KEY = "global"


def _extract_preference(feedback: str) -> Optional[str]:
    """
    Heuristically decide whether a piece of feedback is a reusable preference.
    """
    text = feedback.lower()
    keywords = [
        "don't generate repeated",
        "don't generate the repeated",
        "avoid duplicate",
        "no duplicate",
        "too many test cases",
        "fewer test cases",
    ]
    if any(k in text for k in keywords):
        return feedback.strip()
    return None


def remember_feedback(feedback: str, ticket_id: Optional[str] = None) -> None:
    """
    Store significant user feedback into long-term memory.
    """
    pref = _extract_preference(feedback)
    if not pref:
        return

    key: Tuple[str, str] = (_PREF_NS, _PREF_KEY)
    existing: List[dict[str, Any]] = []
    try:
        record = _store.mget([key])[0]
        if record is not None and "value" in record:
            existing = list(record["value"])
    except Exception:
        existing = []

    entry: dict[str, Any] = {"text": pref}
    if ticket_id:
        entry["ticket_id"] = ticket_id
    existing.append(entry)

    _store.mset([(key, {"value": existing})])


def load_preferences() -> List[str]:
    """
    Retrieve remembered preference strings.
    """
    key: Tuple[str, str] = (_PREF_NS, _PREF_KEY)
    try:
        record = _store.mget([key])[0]
        if record is None or "value" not in record:
            return []
        return [str(e.get("text", "")).strip() for e in record["value"] if e.get("text")]
    except Exception:
        return []

