from pathlib import Path

from sportoto.interface import SportTotoService, load_fixture_file
from sportoto.tool_boundary import ResearchToolRegistry
from sportoto.adapter_contracts import AdapterRegistry

FIXTURES = "data/current_sportoto_list_2026-08-21.json"
PREDICTIONS = "data/predictions/2026-08-21-predictions_HYBRID_TRANSFER_COUNTS.json"


def test_full_15_match_domain_workflow(tmp_path):
    service = SportTotoService(ResearchToolRegistry(AdapterRegistry()))
    result = service.run(run_id="2026W34", fixtures=load_fixture_file(FIXTURES), prediction_artifact=PREDICTIONS, journal_path=str(tmp_path / "journal.jsonl"))
    assert result.status == "completed"
    assert result.fixture_count == 15
    assert result.completed_stages[-3:] == ("decision", "journal", "h15")
    assert result.summary["scenarios"] >= 1
    assert Path(result.artifacts["journal"]).read_text().count("\n") == 15


def test_domain_interface_returns_failure_contract(tmp_path):
    service = SportTotoService(ResearchToolRegistry(AdapterRegistry()))
    result = service.run(run_id="bad", fixtures=load_fixture_file(FIXTURES), prediction_artifact="missing.json", journal_path=str(tmp_path / "journal.jsonl"))
    assert result.status == "failed"
    assert result.failed_stage == "prediction"
    assert result.error
