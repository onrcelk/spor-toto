"""Optional MCP server exposing only high-level Sport Toto operations."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP

from .adapter_contracts import AdapterRegistry
from .interface import SportTotoService
from .tool_boundary import ResearchToolRegistry

mcp = FastMCP("sportoto")


def _service() -> SportTotoService:
    # Provider registration remains a domain deployment concern; no overrides are exposed here.
    return SportTotoService(ResearchToolRegistry(AdapterRegistry()))


@mcp.tool(name="sportoto_run")
def sportoto_run(run_id: str, fixtures: list[dict[str, Any]], prediction_artifact: str, journal_path: str) -> dict[str, Any]:
    """Run the deterministic Sport Toto workflow; probabilities and policy cannot be overridden."""
    return _service().run(run_id=run_id, fixtures=fixtures, prediction_artifact=prediction_artifact, journal_path=journal_path).to_dict()


@mcp.tool(name="sportoto_inspect")
def sportoto_inspect(journal_path: str, match_id: str | None = None, record_id: str | None = None) -> dict[str, Any]:
    """Inspect an existing final journal record without rerunning or modifying the workflow."""
    records = [json.loads(line) for line in Path(journal_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    matches = [record for record in records if (not match_id or record.get("match_id") == match_id) and (not record_id or record.get("record_id") == record_id)]
    if not matches:
        return {"status": "not_found", "records": []}
    return {"status": "ok", "records": matches}


if __name__ == "__main__":
    mcp.run()
