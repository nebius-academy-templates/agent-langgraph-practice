from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence

from langchain_core.tools import BaseTool

try:
    from langchain_mcp_adapters.client import MultiServerMCPClient  # type: ignore
except Exception:  # pragma: no cover
    MultiServerMCPClient = None  # type: ignore[assignment]


@dataclass
class MCPToolset:
    """Container passed into nodes to avoid importing tools directly."""

    tools: Dict[str, Any]

    def get(self, name: str) -> Any:
        return self.tools.get(name)


class MCPLifecycle:
    """
    MCP lifecycle manager and tool loader.

    This intentionally keeps node code decoupled from MCP adapters: nodes receive
    an injected `MCPToolset` and call tools by name.
    """

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self._started = False
        self._toolset: Optional[MCPToolset] = None

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        self._toolset = MCPToolset(tools={})

    def stop(self) -> None:
        self._started = False
        self._toolset = None

    def toolset(self) -> MCPToolset:
        if not self._started or self._toolset is None:
            raise RuntimeError("MCP not started. Call start() first.")
        return self._toolset

    def load_config(self) -> Dict[str, Any]:
        data = json.loads(self.config_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Invalid mcp_config.json: root must be an object.")
        return data

    def load_tools(self) -> MCPToolset:
        """
        Load tools using langchain-mcp-adapters if configured.

        This skeleton keeps the loader lightweight; if you have MCP servers
        running, you can extend this to create real tool instances.
        """
        self.start()
        config = {}
        try:
            config = self.load_config()
        except FileNotFoundError:
            config = {}

        # Placeholder: we expose the raw config for debugging and future wiring.
        self._toolset = MCPToolset(tools={"mcp_config": config})
        return self._toolset


def build_mcp(config_path: Path) -> MCPLifecycle:
    return MCPLifecycle(config_path=config_path)


def list_tool_names(toolset: MCPToolset) -> List[str]:
    return sorted(toolset.tools.keys())


_printed_notion_tools = False


def _require_notion_api_key() -> str:
    # Settings.load() calls load_dotenv() so .env is available via os.environ,
    # but we also tolerate direct usage.
    key = os.environ.get("NOTION_API_KEY")
    if not key:
        try:
            from dotenv import load_dotenv  # type: ignore

            load_dotenv()
        except Exception:
            pass
        key = os.environ.get("NOTION_API_KEY")
    if not key:
        raise RuntimeError("NOTION_API_KEY is not set in the environment.")
    return key


def _build_notion_server_config() -> Dict[str, Any]:
    """
    Build notion MCP server config at runtime, injecting NOTION_API_KEY into
    OPENAPI_MCP_HEADERS.
    """
    notion_key = _require_notion_api_key()

    headers_json = json.dumps(
        {"Authorization": f"Bearer {notion_key}", "Notion-Version": "2022-06-28"}
    )

    # This matches the shape used by langchain-mcp-adapters.
    return {
        "notion": {
            "transport": "stdio",
            "command": "npx",
            "args": ["-y", "@notionhq/notion-mcp-server"],
            "env": {"OPENAPI_MCP_HEADERS": headers_json},
        }
    }


def _tool_name(t: BaseTool) -> str:
    # LangChain tools expose `.name`
    return getattr(t, "name", "") or ""


async def get_notion_tools() -> List[BaseTool]:
    """
    Load Notion MCP tools using MultiServerMCPClient.
    """
    if MultiServerMCPClient is None:
        raise RuntimeError(
            "langchain-mcp-adapters is not available. Install dependencies first."
        )

    server_config = _build_notion_server_config()
    logger = logging.getLogger(__name__)

    client = MultiServerMCPClient(server_config)
    tools: Sequence[BaseTool] = await client.get_tools()

    global _printed_notion_tools
    if not _printed_notion_tools:
        names = ", ".join(sorted(_tool_name(t) for t in tools))
        logger.info("Notion MCP tools available: %s", names)
        _printed_notion_tools = True

    wanted = {"notion-search", "notion-fetch-page"}
    filtered = [t for t in tools if _tool_name(t) in wanted]

    # If exact names differ, fall back to a best-effort match.
    if len(filtered) < 2:
        filtered = [
            t
            for t in tools
            if any(k in _tool_name(t).lower() for k in ("notion", "search", "fetch"))
        ]

    return filtered


@contextmanager
def load_notion_tools() -> Iterator[List[BaseTool]]:
    """
    Synchronous wrapper around `get_notion_tools()` for use in sync contexts.

    Usage:
        with load_notion_tools() as tools:
            ...
    """
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        tools = loop.run_until_complete(get_notion_tools())
        yield tools
    finally:
        try:
            asyncio.set_event_loop(None)
        finally:
            loop.close()
