from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from train_real_walkforward import load_and_enrich


def test_load_and_enrich_can_add_transfer_features(tmp_path: Path):
    match_path = tmp_path / "matches.parquet"
    pd.DataFrame([{
        "kickoff_iso": "2025-01-01T00:00:00+00:00",
        "home_team": "Fenerbahçe A.Ş.", "away_team": "Konyaspor",
        "actual_1x2": 0,
        "home_goals_avg": 1, "away_goals_avg": 1,
        "home_conceded_avg": 1, "away_conceded_avg": 1,
        "home_form_points": 1, "away_form_points": 1,
        "h2h_home_win_rate": .5, "h2h_draw_rate": .25, "h2h_away_win_rate": .25,
        "home_xg_avg": 1, "away_xg_avg": 1, "is_derby": False,
        "rest_days_home": 7, "rest_days_away": 7, "elo_diff": 0,
    }]).to_parquet(match_path, index=False)
    transfer_path = tmp_path / "transfers.csv"
    pd.DataFrame([{
        "transfer_date": "2024-07-01", "from_club_name": "Other",
        "to_club_name": "Fenerbahce", "transfer_fee": "1000000",
    }]).to_csv(transfer_path, index=False)

    result = load_and_enrich(match_path, transfer_path)

    assert result.loc[0, "home_transfer_in_count_365"] == 1
