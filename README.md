# LangGraph QA Agent (scaffold)

This repo is a starter structure for a LangGraph-based QA agent with MCP tool loading.

## Quickstart

```bash
python3 -m pip install -e .
python3 main.py
```

## Layout

- `qa_agent/`: package (state, nodes, graph, config, MCP loader)
- `mcp_config.json`: MCP server config (edit to your environment)
- `main.py`: minimal runnable entrypoint
