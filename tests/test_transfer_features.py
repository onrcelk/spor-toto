from pathlib import Path

import pandas as pd

from sportoto.transfer_features import build_transfer_features


def test_transfer_features_use_only_transfers_before_kickoff(tmp_path: Path):
    path = tmp_path / "transfers.csv"
    pd.DataFrame([
        {"transfer_date": "2024-07-01", "from_club_name": "Other", "to_club_name": "Fenerbahce", "transfer_fee": "1000000"},
        {"transfer_date": "2024-12-01", "from_club_name": "Fenerbahce", "to_club_name": "Other", "transfer_fee": "500000"},
        {"transfer_date": "2025-02-01", "from_club_name": "Other", "to_club_name": "Fenerbahce", "transfer_fee": "9000000"},
    ]).to_csv(path, index=False)
    matches = pd.DataFrame([{
        "kickoff_iso": "2025-01-01T00:00:00+00:00",
        "home_team": "Fenerbahçe A.Ş.",
        "away_team": "Konyaspor",
    }])

    result = build_transfer_features(path, matches)

    assert result.loc[0, "home_transfer_in_count_365"] == 1
    assert result.loc[0, "home_transfer_out_count_365"] == 1
    assert result.loc[0, "home_transfer_net_fee_365"] == 500000
    assert result.loc[0, "home_transfer_in_count_365"] != 2
