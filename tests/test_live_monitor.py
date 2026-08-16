from dataclasses import dataclass

from sportoto.live_monitor import snapshot_sportoto_list


@dataclass(frozen=True)
class Row:
    match_index: int
    home_team: str
    away_team: str
    date_text: str
    time_text: str
    source_url: str
    fetched_at: str
    competition: str = "Spor Toto"


def test_snapshot_records_change_and_no_change(tmp_path):
    row = Row(1, "A", "B", "01.01.2030", "20:00", "source", "now")
    output = tmp_path / "snapshots.jsonl"
    first = snapshot_sportoto_list(output, lambda: [row])
    second = snapshot_sportoto_list(output, lambda: [row])
    assert first["changed"] is True
    assert second["changed"] is False
    assert len(output.read_text(encoding="utf-8").splitlines()) == 2
