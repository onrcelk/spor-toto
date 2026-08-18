"""Gerçek hafta listesini tarihsel training verisinden üretilen özelliklerle modele besler.

DÜZELTME (2026-08-17): _team_aggregates artık takımın EV+DEPLASMAN tüm maçlarını
normalize_team_name ile eşleştirip genel gol/güç ortalamasını hesaplıyor. Önceki
sürümde (a) isim normalize edilmediği için 2025-26 takımları parquet'te bulunamıyor
(sample_size=0 -> lig ortalaması -> tüm SL maçları aynı X tahmini) ve (b) sadece ev
maçları filtrelenip yanlış gol ortalaması hesaplanıyordu.
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
from .transfer_features import COUNT_FEATURE_COLUMNS, FEATURE_COLUMNS as TRANSFER_FEATURE_COLS, build_transfer_features

DEFAULT_LIST = "data/current_sportoto_list_2026-08-21.json"
DEFAULT_HISTORY = "data/sportoto_master_training.parquet"
DEFAULT_MODEL = "data/models/sportoto_master_model.joblib"
DEFAULT_OUTPUT = "data/predictions/2026-08-21-predictions.json"
LAST_N = 8


def _team_aggregates(frame: pd.DataFrame, team: str, before: pd.Timestamp, last_n: int = LAST_N) -> dict:
    team_n = normalize_team_name(team)
    mask = (frame["home_team"].map(normalize_team_name) == team_n) | \
           (frame["away_team"].map(normalize_team_name) == team_n)
    rows = frame[mask & (frame["kickoff_iso"] < before)].copy()
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
    gf, ga, xg, form = [], [], [], []
    for _, r in rows.iterrows():
        is_home = normalize_team_name(str(r["home_team"])) == team_n
        # parquet'te hazır feature'lar: takımın o maç öncesi genel ortalamaları
        gf.append(float(r["home_goals_avg"]) if is_home else float(r["away_goals_avg"]))
        ga.append(float(r["away_conceded_avg"]) if is_home else float(r["home_conceded_avg"]))
        xg.append(float(r["home_xg_avg"]) if is_home else float(r["away_xg_avg"]))
        form.append(float(r["home_form_points"]) if is_home else float(r["away_form_points"]))
    return {
        "home_goals_avg": float(np.mean(gf)),
        "away_goals_avg": float(np.mean(ga)),
        "home_conceded_avg": float(np.mean(ga)),
        "away_conceded_avg": float(np.mean(gf)),
        "home_xg_avg": float(np.mean(xg)),
        "away_xg_avg": float(np.mean(xg)),
        "home_form_points": float(np.mean(form)),
        "away_form_points": float(np.mean(form)),
        "elo_diff": float(rows["elo_diff"].iloc[-1]) if "elo_diff" in rows.columns else 0.0,
        "sample_size": int(len(rows)),
    }


def _h2h(frame: pd.DataFrame, home: str, away: str, before: pd.Timestamp) -> dict:
    hn, an = normalize_team_name(home), normalize_team_name(away)
    mask = (
        ((frame["home_team"].map(normalize_team_name) == hn) &
         (frame["away_team"].map(normalize_team_name) == an)) |
        ((frame["home_team"].map(normalize_team_name) == an) &
         (frame["away_team"].map(normalize_team_name) == hn))
    )
    sub = frame[mask & (frame["kickoff_iso"] < before)].copy()
    if sub.empty:
        return {"h2h_home_win_rate": 0.5, "h2h_draw_rate": 0.25, "h2h_away_win_rate": 0.25, "h2h_sample": 0}
    home_wins = draws = away_wins = 0
    for _, r in sub.iterrows():
        rh = normalize_team_name(str(r["home_team"])) == hn
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
    transfer_csv: str | None = None,
    transfer_mode: str = "counts",
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
        if transfer_csv:
            transfer_row = pd.DataFrame([{
                "kickoff_iso": ko.isoformat(), "home_team": home, "away_team": away,
            }])
            transfer_values = build_transfer_features(transfer_csv, transfer_row).iloc[0]
            transfer_cols = COUNT_FEATURE_COLUMNS if transfer_mode == "counts" else TRANSFER_FEATURE_COLS
            extra_features = [float(transfer_values[col]) for col in transfer_cols]
            pred = model.predict_with_extra_features(mf, extra_features)
        else:
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
                "transfer_features": bool(transfer_csv),
                "transfer_mode": transfer_mode if transfer_csv else None,
            },
        })

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "list_source": list_path,
        "model": model_path,
        "transfer_csv": transfer_csv,
        "transfer_mode": transfer_mode,
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
              f"(O{p['pred_over_2_5']}) | sz={p['features']['home_sample_size']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
