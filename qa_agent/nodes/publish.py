from __future__ import annotations

from typing import Dict, Optional

from ..state import QAState


def publish(state: QAState, *, tools: Optional[object] = None) -> Dict:
    """
    Placeholder for publishing (Linear/Notion/etc). Uses injected tools only.
    """
    _ = tools
    return {"published": True}
