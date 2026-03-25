from __future__ import annotations

from typing import Dict, Optional

from ..state import QAState


def check_existing(state: QAState, *, tools: Optional[object] = None) -> Dict:
    """
    Check if an answer/work item already exists.

    `tools` is injected (e.g. MCPToolset). We do not import tool implementations here.
    """
    _ = tools  # reserved for future use
    return {"existing": None}
