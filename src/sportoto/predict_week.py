"""Gerçek hafta listesini tarihsel training verisinden üretilen özelliklerle modele besler.

Bu modül:
- Kullanıcının verdiği 21-25 Ağu Spor Toto listesini okur.
- Her takım için training parquet'inden son N maçın ortalamalarını hesaplar
  (atılan/yenen gol, xG, form puanı).
- İki takım arasındaki H2H oranlarını hesaplar.
- Hazır modeli (sportoto_master_model.joblib) yükleyip 15 maçın 1X2 + Alt/Üst
  tahminini üretir.
- Tahminleri JSON olarak kaydeder.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from .features import MatchFeatures
from .identity import normalize_team_name
from .model import MatchModel

DEFAULT_LIST = "data/current_sportoto_list_2026-08-21.json"
DEFAULT_HISTORY = "data/sportoto_master_training.parquet"
DEFAULT_MODEL = "data/models/sportoto_master_model.joblib"
DEFAULT_OUTPUT = "data/predictions/2026-08-21-predictions.json"
LAST_N = 8


def _casefold_eq(a: str, b: str) -> bool:
    return normalize_team_name(a) == normalize_team_name(b)


def _team_rows(frame: pd.DataFrame, team: str) -> pd.DataFrame:
    mask = frame["home_team"].astype(str).str.casefold() == team.casefold()
    mask |= frame["away_team"].astype(str).str.casefold() == team.casefold()
    return frame[mask].copy()


def _team_aggregates(frame: pd.DataFrame, team: str, before: pd.Timestamp, last_n: int = LAST_N) -> dict:
    rows = _team_rows(frame, team)
    rows = rows[rows["kickoff_iso"] < before].copy()
    rows = rows.sort_values("kickoff_iso").tail(last_n)
    if rows.empty:
        return {
            "home_goals_avg": 0.0, "away_goals_avg": 0.0,
            "home_conceded_avg": 0.0, "away_conceded_avg": 0.0,
            "home_xg_avg": 0.0, "away_xg_avg": 0.0,
            "home_form_points": 0.0, "away_form_points": 0.0,
            "elo_diff": 0.0,
            "sample_size": 0,
        }
    home = rows[rows["home_team"].astype(str).str.casefold() == team.casefold()]
    away = rows[rows["away_team"].astype(str).str.casefold() == team.casefold()]
    goals_for_home = home["home_goals_avg"].mean() if not home.empty else np.nan
    conceded_home = home["home_conceded_avg"].mean() if not home.empty else np.nan
    xg_home = home["home_xg_avg"].mean() if not home.empty else np.nan
    form_home = home["home_form_points"].mean() if not home.empty else np.nan
    goals_for_away = away["away_goals_avg"].mean() if not away.empty else np.nan
    conceded_away = away["away_conceded_avg"].mean() if not away.empty else np.nan
    xg_away = away["away_xg_avg"].mean() if not away.empty else np.nan
    form_away = away["away_form_points"].mean() if not away.empty else np.nan
    elo_diff = rows["elo_diff"].iloc[-1] if "elo_diff" in rows.columns else 0.0
    return {
        "home_goals_avg": float(np.nanmean([goals_for_home])),
        "away_goals_avg": float(np.nanmean([goals_for_away])),
        "home_conceded_avg": float(np.nanmean([conceded_home])),
        "away_conceded_avg": float(np.nanmean([conceded_away])),
        "home_xg_avg": float(np.nanmean([xg_home])),
        "away_xg_avg": float(np.nanmean([xg_away])),
        "home_form_points": float(np.nanmean([form_home])),
        "away_form_points": float(np.nanmean([form_away])),
        "elo_diff": float(elo_diff),
        "sample_size": int(len(rows)),
    }


def _h2h(frame: pd.DataFrame, home: str, away: str, before: pd.Timestamp) -> dict:
    mask = (
        ((frame["home_team"].astype(str).str.casefold() == home.casefold()) &
         (frame["away_team"].astype(str).str.casefold() == away.casefold()))
        |
        ((frame["home_team"].astype(str).str.casefold() == away.casefold()) &
         (frame["away_team"].astype(str).str.casefold() == home.casefold()))
    )
    sub = frame[mask & (frame["kickoff_iso"] < before)].copy()
    if sub.empty:
        return {"h2h_home_win_rate": 0.5, "h2h_draw_rate": 0.25, "h2h_away_win_rate": 0.25, "h2h_sample": 0}
    home_wins = draws = away_wins = 0
    for _, r in sub.iterrows():
        rh = str(r["home_team"]).casefold() == home.casefold()
        res = r["actual_1x2"]
        if res == 1:
            draws += 1
        elif res == 0:
            home_wins += 1 if rh else 0
            away_wins += 0 if rh else 1
        elif res == 2:
            away_wins += 1 if rh else 0
            home_wins += 0 if rh else 1
    n = len(sub)
    return {
        "h2h_home_win_rate": home_wins / n,
        "h2h_draw_rate": draws / n,
        "h2h_away_win_rate": away_wins / n,
        "h2h_sample": n,
    }


def _parse_kickoff(item: dict) -> pd.Timestamp:
    kt = item.get("date_text", item.get("date", ""))
    tt = item.get("time_text", item.get("time", ""))
    ts = pd.to_datetime(f"{kt} {tt}", dayfirst=True, utc=True, errors="coerce")
    if pd.isna(ts):
        ts = pd.Timestamp.now(tz="UTC")
    return ts


def build_predictions(
    list_path: str = DEFAULT_LIST,
    history_path: str = DEFAULT_HISTORY,
    model_path: str = DEFAULT_MODEL,
    output: str = DEFAULT_OUTPUT,
    last_n: int = LAST_N,
) -> dict:
    frame = pd.read_parquet(Path(history_path).expanduser())
    frame["kickoff_iso"] = pd.to_datetime(frame["kickoff_iso"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["kickoff_iso", "actual_1x2"])

    lst = json.loads(Path(list_path).expanduser().read_text(encoding="utf-8"))
    matches = lst["matches"] if isinstance(lst, dict) else lst

    model = MatchModel(Path(model_path).expanduser())

    league_avg = {
        "home_goals_avg": float(frame["home_goals_avg"].mean()),
        "away_goals_avg": float(frame["away_goals_avg"].mean()),
        "home_conceded_avg": float(frame["home_conceded_avg"].mean()),
        "away_conceded_avg": float(frame["away_conceded_avg"].mean()),
        "home_xg_avg": float(frame["home_xg_avg"].mean()),
        "away_xg_avg": float(frame["away_xg_avg"].mean()),
        "home_form_points": float(frame["home_form_points"].mean()),
        "away_form_points": float(frame["away_form_points"].mean()),
        "elo_diff": 0.0,
    }

    predictions = []
    for item in matches:
        home = item["home_team"]
        away = item["away_team"]
        ko = _parse_kickoff(item)
        ha = _team_aggregates(frame, home, ko, last_n)
        aa = _team_aggregates(frame, away, ko, last_n)
        h2h = _h2h(frame, home, away, ko)
        # zero-history veya NaN kalan takımlar için lig ortalamasıyla tamamla
        def _fill(agg: dict) -> dict:
            out = dict(agg)
            for k, lig in league_avg.items():
                val = agg.get(k)
                if val is None or (isinstance(val, float) and np.isnan(val)) or val in (0, 0.0):
                    out[k] = float(lig)
                else:
                    out[k] = float(val)
            return out
        ha = _fill(ha)
        aa = _fill(aa)

        mf = MatchFeatures(
            match_id=f"M{item.get('match_index', len(predictions)+1):02d}",
            home_team=home, away_team=away,
            league=item.get("competition", "Spor Toto mixed"),
            kickoff_iso=ko.isoformat(),
            home_goals_avg=ha["home_goals_avg"], away_goals_avg=aa["away_goals_avg"],
            home_conceded_avg=ha["home_conceded_avg"], away_conceded_avg=aa["away_conceded_avg"],
            home_form_points=ha["home_form_points"], away_form_points=aa["away_form_points"],
            h2h_home_win_rate=h2h["h2h_home_win_rate"], h2h_draw_rate=h2h["h2h_draw_rate"],
            h2h_away_win_rate=h2h["h2h_away_win_rate"],
            home_xg_avg=ha["home_xg_avg"], away_xg_avg=aa["away_xg_avg"],
            is_derby=False,
            rest_days_home=7, rest_days_away=7,
            elo_diff=ha["elo_diff"] - aa["elo_diff"],
        )
        pred = model.predict(mf)
        predictions.append({
            "match_id": mf.match_id,
            "match_index": item.get("match_index"),
            "home_team": home, "away_team": away,
            "kickoff": ko.isoformat(),
            "pred_home_win": round(pred.pred_home_win, 3),
            "pred_draw": round(pred.pred_draw, 3),
            "pred_away_win": round(pred.pred_away_win, 3),
            "pred_over_2_5": round(pred.pred_over_2_5, 3),
            "pred_under_2_5": round(pred.pred_under_2_5, 3),
            "confidence": round(pred.confidence, 3),
            "predicted_1x2": pred.predicted_1x2,
            "predicted_ou": pred.predicted_ou,
            "features": {
                "home_form_points": round(ha["home_form_points"], 2),
                "away_form_points": round(aa["away_form_points"], 2),
                "home_xg_avg": round(ha["home_xg_avg"], 2),
                "away_xg_avg": round(aa["away_xg_avg"], 2),
                "h2h_sample": h2h["h2h_sample"],
                "home_sample_size": ha["sample_size"],
                "away_sample_size": aa["sample_size"],
            },
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "list_source": list_path,
        "model": model_path,
        "match_count": len(predictions),
        "predictions": predictions,
    }
    out = Path(output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    payload = build_predictions()
    print(f"Predictions: {payload['match_count']} matches -> {DEFAULT_OUTPUT}")
    for p in payload["predictions"]:
        print(f"  M{p['match_index']:>2} {p['home_team'][:20]:20} - {p['away_team'][:20]:20} "
              f"=> {p['predicted_1x2']} (conf {p['confidence']}) | O/U {p['predicted_ou']} "
              f"(O{p['pred_over_2_5']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
