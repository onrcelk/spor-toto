"""Leakage-safe Transfermarkt transfer features for match rows."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .identity import normalize_team_name, resolve_team


FEATURE_COLUMNS = [
    "home_transfer_in_count_365",
    "home_transfer_out_count_365",
    "home_transfer_net_fee_365",
    "away_transfer_in_count_365",
    "away_transfer_out_count_365",
    "away_transfer_net_fee_365",
]
COUNT_FEATURE_COLUMNS = [
    "home_transfer_in_count_365",
    "home_transfer_out_count_365",
    "away_transfer_in_count_365",
    "away_transfer_out_count_365",
]


def _money(value: object) -> float:
    if value is None or pd.isna(value):
        return 0.0
    text = str(value).strip().replace("€", "").replace(",", "")
    if text in {"", "-", "?", "nan", "None"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def build_transfer_features(
    transfers_path: str | Path,
    matches: pd.DataFrame,
    window_days: int = 365,
) -> pd.DataFrame:
    """Attach pre-kickoff Transfermarkt transfer activity to match rows.

    Every match only sees transfers with ``transfer_date < kickoff`` and within
    the preceding ``window_days``. Unknown teams remain zero rather than being
    fabricated or joined by ordinal position.
    """
    transfers = pd.read_csv(transfers_path)
    required = {"transfer_date", "from_club_name", "to_club_name", "transfer_fee"}
    missing = required - set(transfers.columns)
    if missing:
        raise ValueError(f"Transfer dataset missing columns: {sorted(missing)}")

    transfers = transfers.copy()
    transfers["_date"] = pd.to_datetime(transfers["transfer_date"], errors="coerce", utc=True)
    if transfers["_date"].isna().any():
        transfers = transfers[transfers["_date"].notna()].copy()
    transfers["_from"] = transfers["from_club_name"].map(resolve_team).map(normalize_team_name)
    transfers["_to"] = transfers["to_club_name"].map(resolve_team).map(normalize_team_name)
    transfers["_fee"] = transfers["transfer_fee"].map(_money)

    output = matches.copy()
    kickoff = pd.to_datetime(output["kickoff_iso"], format="mixed", dayfirst=True, utc=True, errors="coerce")
    if kickoff.isna().any():
        raise ValueError("Match rows contain unparseable kickoff_iso values")

    rows: list[dict[str, float]] = []
    for target in kickoff:
        start = target - pd.Timedelta(days=window_days)
        visible = transfers[(transfers["_date"] < target) & (transfers["_date"] >= start)]
        row: dict[str, float] = {}
        for side, team_col in (("home", "home_team"), ("away", "away_team")):
            # Index by the corresponding match row below; populated after loop.
            row[f"{side}_transfer_in_count_365"] = 0
            row[f"{side}_transfer_out_count_365"] = 0
            row[f"{side}_transfer_net_fee_365"] = 0.0
        rows.append(row)

    for idx, target in enumerate(kickoff):
        start = target - pd.Timedelta(days=window_days)
        visible = transfers[(transfers["_date"] < target) & (transfers["_date"] >= start)]
        for side, team_col in (("home", "home_team"), ("away", "away_team")):
            team = normalize_team_name(resolve_team(str(output.iloc[idx][team_col])))
            incoming = visible[visible["_to"] == team]
            outgoing = visible[visible["_from"] == team]
            rows[idx][f"{side}_transfer_in_count_365"] = float(len(incoming))
            rows[idx][f"{side}_transfer_out_count_365"] = float(len(outgoing))
            rows[idx][f"{side}_transfer_net_fee_365"] = float(incoming["_fee"].sum() - outgoing["_fee"].sum())

    return pd.concat([output.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


__all__ = ["FEATURE_COLUMNS", "COUNT_FEATURE_COLUMNS", "build_transfer_features"]
