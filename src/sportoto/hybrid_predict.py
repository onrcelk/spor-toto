"""Hibrit tahmin: Türk maçları Süper Lig modeli, Avrupa maçları genel model ile.

21-25 Ağu listesindeki maçları ikiye ayırır:
- Süper Lig takımları (Türkiye) -> data/models/superlig_model.joblib
- Avrupa/diğer takımlar -> data/models/sportoto_master_model.joblib

Her iki modeli de aynı tarihsel özellik çıkarımıyla çalıştırır ve sonuçları birleştirir.
"""
from __future__ import annotations

import json
from pathlib import Path

from .predict_week import build_predictions

SUPERLIG_TEAMS = {
    "erzurumspor", "galatasaray", "caykurrizespor", "samsunspor", "corum",
    "kasimpasa", "fenerbahce", "konyaspor", "eyupspor", "gaziantep",
    "trabzonspor", "basaksehir", "alanyaspor", "besiktas", "goztepe",
    "genclerbirligi", "kocaelispor", "amed",
}


def _is_superlig(home: str, away: str) -> bool:
    from .identity import normalize_team_name
    h = normalize_team_name(home)
    a = normalize_team_name(away)
    return h in SUPERLIG_TEAMS and a in SUPERLIG_TEAMS


def build_hybrid(
    list_path: str = "data/current_sportoto_list_2026-08-21.json",
    history_sl: str = "data/superlig_training_2022_2024.parquet",
    history_general: str = "data/sportoto_master_training.parquet",
    model_sl: str = "data/models/superlig_model.joblib",
    model_general: str = "data/models/sportoto_master_model.joblib",
    output: str = "data/predictions/2026-08-21-predictions_HYBRID.json",
) -> dict:
    lst = json.loads(Path(list_path).expanduser().read_text(encoding="utf-8"))
    matches = lst["matches"] if isinstance(lst, dict) else lst

    sl_idx = [m["match_index"] for m in matches if _is_superlig(m["home_team"], m["away_team"])]
    gen_idx = [m["match_index"] for m in matches if m["match_index"] not in sl_idx]

    sl_preds = {}
    if sl_idx:
        p = build_predictions(list_path, history_sl, model_sl,
                              "data/predictions/_sl_tmp.json")
        sl_preds = {x["match_index"]: x for x in p["predictions"]}
    gen_preds = {}
    if gen_idx:
        p = build_predictions(list_path, history_general, model_general,
                              "data/predictions/_gen_tmp.json")
        gen_preds = {x["match_index"]: x for x in p["predictions"]}

    sl_set = set(sl_idx)
    gen_set = set(gen_idx)
    merged = []
    for m in matches:
        if m["match_index"] in sl_set:
            src = sl_preds.get(m["match_index"])
            model_used = "superlig"
        else:
            src = gen_preds.get(m["match_index"])
            model_used = "general"
        if src is None:
            continue
        src = dict(src)
        src["model_used"] = model_used
        merged.append(src)

    payload = {
        "generated_at": json.loads(Path("data/predictions/2026-08-21-predictions.json").read_text(encoding="utf-8"))["generated_at"] if Path("data/predictions/2026-08-21-predictions.json").exists() else "",
        "strategy": "hybrid: TR matches->SuperLig model, others->general model",
        "superlig_match_count": len(sl_idx),
        "general_match_count": len(gen_idx),
        "match_count": len(merged),
        "predictions": merged,
    }
    out = Path(output).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    p = build_hybrid()
    print(f"Hybrid predictions: {p['match_count']} (SL={p['superlig_match_count']}, GEN={p['general_match_count']}) -> data/predictions/2026-08-21-predictions_HYBRID.json")
    for m in p["predictions"]:
        print(f"  M{m['match_index']:>2} {m['home_team'][:18]:18} - {m['away_team'][:18]:18} => {m['predicted_1x2']} ({m['model_used']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
