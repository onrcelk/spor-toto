import json

from sportoto.interface import load_fixture_file
from sportoto.mcp_server import mcp, sportoto_inspect, sportoto_run


def test_mcp_registers_only_high_level_tools():
    names = {tool.name for tool in mcp._tool_manager.list_tools()}
    assert names == {"sportoto_run", "sportoto_inspect"}
    assert "set_probability" not in names
    assert "force_banko" not in names


def test_mcp_run_and_inspect(tmp_path):
    journal = tmp_path / "journal.jsonl"
    result = sportoto_run("mcp-test", load_fixture_file("data/current_sportoto_list_2026-08-21.json"), "data/predictions/2026-08-21-predictions_HYBRID_TRANSFER_COUNTS.json", str(journal))
    assert result["status"] == "completed"
    inspected = sportoto_inspect(str(journal), match_id="M04")
    assert inspected["status"] == "ok"
    assert len(inspected["records"]) == 1
    assert inspected["records"][0]["run_id"] == "mcp-test"
