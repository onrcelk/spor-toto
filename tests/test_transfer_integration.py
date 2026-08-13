from pathlib import Path

from sportoto.transfer_integration import TransferSignal, fetch_transfer_signals, append_signals


def test_fetch_transfer_signals_returns_list():
    signals = fetch_transfer_signals()
    assert isinstance(signals, list)
    if signals:
        signal = signals[0]
        assert isinstance(signal.team, str)
        assert signal.signal_type in {"transfer", "manager_change"}
        assert signal.url.startswith("http")


def test_append_signals_skips_duplicates(tmp_path: Path):
    target = tmp_path / "signals.jsonl"
    signals = [
        TransferSignal(team="Galatasaray", signal_type="manager_change", title="Yeni TD", url="https://example.com/1", published_iso="2026-01-01T00:00:00+00:00"),
        TransferSignal(team="Fenerbahçe", signal_type="transfer", title="Transfer", url="https://example.com/2", published_iso="2026-01-02T00:00:00+00:00"),
    ]
    append_signals(signals, target)
    append_signals(signals, target)
    lines = [line for line in target.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) == 2
