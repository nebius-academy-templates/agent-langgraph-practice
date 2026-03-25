from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """Runtime configuration loaded from env and local files."""

    anthropic_api_key: Optional[str] = Field(default=None, repr=False)
    langsmith_api_key: Optional[str] = Field(default=None, repr=False)
    langsmith_project: Optional[str] = None

    mcp_config_path: Path = Field(default_factory=lambda: Path("mcp_config.json"))

    @classmethod
    def load(cls) -> "Settings":
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            # Allow running before dependencies are installed.
            pass
        import os

        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            langsmith_api_key=os.getenv("LANGSMITH_API_KEY"),
            langsmith_project=os.getenv("LANGSMITH_PROJECT"),
            mcp_config_path=Path(os.getenv("MCP_CONFIG_PATH", "mcp_config.json")),
        )
