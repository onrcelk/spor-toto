"""API-Sports'tan çekilen gerçek Süper Lig (2022-2024) verisini model training formatına dönüştürür.

Giriş: data/live/api_sports_superlig_2022_2024.json
Çıkış: data/superlig_training_2022_2024.parquet (model.py ile uyumlu 14 özellik)

Her satır bir maç; özellikler o maçtan ÖNCEki son N maçın ortalamalarıdır
(leakage'sız). Eksik geçmiş için global ortalama kullanılır.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

INPUT = "data/live/api_sports_superlig_2022_2024.json"
OUTPUT = "data/superlig_training_2022_2024.parquet"
LAST_N = 8


def _to_ts(iso: str) -> pd.Timestamp:
    return pd.to_datetime(iso, utc=True, errors="coerce")


def build_frame(input_path: str = INPUT, output: str = OUTPUT, last_n: int = LAST_N) -> pd.DataFrame:
    rows = json.loads(Path(input_path).expanduser().read_text(encoding="utf-8"))
    df = pd.DataFrame(rows)
    df["kickoff"] = df["kickoff_iso"].map(_to_ts)
    df = df.dropna(subset=["kickoff"]).sort_values("kickoff").reset_index(drop=True)
    df["actual_1x2"] = df.apply(
        lambda r: 0 if r["home_goals"] > r["away_goals"] else (2 if r["home_goals"] < r["away_goals"] else 1), axis=1
    )

    # global ortalamalar (ilk maçlar için)
    g_home_g = df["home_goals"].mean()
    g_away_g = df["away_goals"].mean()

    # takım bazlı kümülatif istatistik
    team_stats: dict[str, list] = {}

    def team_avg(team: str, before_idx: int) -> dict:
        hist = team_stats.get(team, [])
        recent = hist[-last_n:]
        if not recent:
            return {"goals": g_home_g, "conceded": g_away_g, "form": 1.5, "xg": (g_home_g + g_away_g) / 2}
        goals = np.mean([h["goals"] for h in recent])
        conceded = np.mean([h["conceded"] for h in recent])
        form = np.mean([h["points"] for h in recent])
        xg = np.mean([h["xg"] for h in recent])
        return {"goals": goals, "conceded": conceded, "form": form, "xg": xg}

    out = []
    for idx, r in df.iterrows():
        home, away = r["home_team"], r["away_team"]
        ha = team_avg(home, idx)
        aa = team_avg(away, idx)
        out.append({
            "match_id": f"sl_{idx}",
            "home_team": home, "away_team": away, "league": "Super Lig",
            "kickoff_iso": r["kickoff"].isoformat(),
            "home_goals_avg": float(ha["goals"]), "away_goals_avg": float(aa["goals"]),
            "home_conceded_avg": float(ha["conceded"]), "away_conceded_avg": float(aa["conceded"]),
            "home_form_points": float(ha["form"]), "away_form_points": float(aa["form"]),
            "h2h_home_win_rate": 0.5, "h2h_draw_rate": 0.25, "h2h_away_win_rate": 0.25,
            "home_xg_avg": float(ha["xg"]), "away_xg_avg": float(aa["xg"]),
            "is_derby": False, "rest_days_home": 7, "rest_days_away": 7,
            "actual_1x2": int(r["actual_1x2"]),
        })
        # bu maçı istatistiğe ekle
        for team, is_home in [(home, True), (away, False)]:
            tg = r["home_goals"] if is_home else r["away_goals"]
            cg = r["away_goals"] if is_home else r["home_goals"]
            pts = 3 if tg > cg else (1 if tg == cg else 0)
            xg = (tg + cg) / 2.0
            team_stats.setdefault(team, []).append({"goals": tg, "conceded": cg, "points": pts, "xg": xg})

    out_df = pd.DataFrame(out)
    Path(output).expanduser().parent.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(Path(output).expanduser(), index=False)
    return out_df


def main() -> int:
    df = build_frame()
    print(f"Super Lig training frame: {len(df)} rows -> {OUTPUT}")
    print("1X2 dist:", df["actual_1x2"].value_counts(normalize=True).round(3).to_dict())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
