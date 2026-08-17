"""Extend the general (multi-league) master training set with the latest
finished European seasons (2425 = 2025-26) from football-data.co.uk.

Downloads E0 (EPL), SP1 (La Liga), D1 (Bundesliga), I1 (Serie A), F1 (Ligue 1)
for 2425, normalizes each row into the same raw shape used by superlig_data,
then appends to the existing 4996-row master parquet (rebuilds features via
superlig_data.build_frame over the combined frame).

Output: data/sportoto_master_training_2026.parquet (updated) + refit model.
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from sportoto.superlig_data import build_frame as build_raw_frame

LEAGUES = {"E0": "EPL", "SP1": "La Liga", "D1": "Bundesliga", "I1": "Serie A", "F1": "Ligue 1"}
BASE = "https://www.football-data.co.uk/mmz4281/2425"
MASTER = Path("data/sportoto_master_training.parquet")
OUT = Path("data/sportoto_master_training_2026.parquet")


def _norm_date(d: str) -> str:
    try:
        return datetime.strptime(d.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return d.strip()


def download_league(code: str, league_name: str) -> list[dict]:
    url = f"{BASE}/{code}.csv"
    with urllib.request.urlopen(url, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for i, row in enumerate(reader):
        hg, ag = row.get("FTHG"), row.get("FTAG")
        if not hg or not ag or hg.strip() == "" or ag.strip() == "":
            continue
        try:
            hg_i, ag_i = int(hg), int(ag)
        except ValueError:
            continue
        date = _norm_date(row.get("Date", ""))
        out.append({
            "match_id": f"fdccouk-2425-{code}-{i}",
            "home_team": row.get("HomeTeam", "").strip(),
            "away_team": row.get("AwayTeam", "").strip(),
            "kickoff_iso": f"{date}T00:00:00+00:00",
            "home_goals": hg_i,
            "away_goals": ag_i,
            "league": league_name,
            "season": "2025-26",
        })
    return out


def main() -> int:
    raw: list[dict] = []
    for code, name in LEAGUES.items():
        rows = download_league(code, name)
        print(f"{name} ({code}): {len(rows)} maç")
        raw.extend(rows)
    print(f"Toplam yeni Avrupa: {len(raw)} maç")

    # write combined raw to a temp json, build features via superlig_data
    tmp = Path("data/live/_euro_2425_raw.json")
    tmp.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    # build features for the new frame (standalone, league-aware)
    new_df = build_raw_frame(str(tmp))
    # tag league from raw mapping (build_raw_frame drops league? check)
    if "league" not in new_df.columns:
        # map back by match_id prefix
        lig_map = {r["match_id"]: r["league"] for r in raw}
        new_df["league"] = new_df["match_id"].map(lig_map).fillna("Unknown")

    # load existing master, append new, dedup
    master = pd.read_parquet(MASTER)
    # keep only feature cols present in both
    feat_cols = [c for c in new_df.columns if c in master.columns]
    new_part = new_df[feat_cols].copy()
    combined = pd.concat([master, new_part], ignore_index=True)
    combined = combined.drop_duplicates(subset=["match_id"]).reset_index(drop=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_parquet(OUT, index=False)
    print(f"Birleşik master: {len(combined)} satır -> {OUT}")
    tmp.unlink(missing_ok=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
