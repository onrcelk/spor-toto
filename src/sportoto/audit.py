"""Maç sonu audit: kaydedilmiş tahminleri gerçek sonuçlarla eşleştirir.

Akış:
- Kayıtlı tahmin dosyasını (data/predictions/...-predictions.json) okur.
- Her maç için gerçek skoru API-Sports (varsa) veya football-data.org'dan çeker.
  (API-Sports Free planı sadece 16-18 Ağu arasına eriştiği için, gelecek hafta
   sonuçları ancak maçlar bittikten sonra çekilebilir.)
- 1X2 hit/miss + Alt/Üst (2.5) hit/miss hesaplar.
- Sonucu JSONL olarak data/live/audit/ altına yazar (her çalıştırmada append).
- Özet rapor döndürür.

NOT: read-only; hiçbir bahis yapmaz, sadece doğrulama kaydı tutar.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .multi_source import fetch_api_sports, fetch_football_data
from .identity import normalize_team_name, resolve_team
from .odds import fetch_fdccouk_results


def _match_real(rows: list[dict], home: str, away: str) -> dict | None:
    nh = resolve_team(home)
    na = resolve_team(away)
    best = None
    for r in rows:
        rh = resolve_team(r.get("home_team", ""))
        ra = resolve_team(r.get("away_team", ""))
        if (rh == nh and ra == na) or (rh == na and ra == nh):
            best = r
            if r.get("home_goals") is not None and r.get("away_goals") is not None:
                return r
    return best


def _result_from_score(home: int | None, away: int | None) -> str | None:
    if home is None or away is None:
        return None
    if home > away:
        return "1"
    if home < away:
        return "2"
    return "X"


def _ou_from_score(home: int | None, away: int | None) -> str | None:
    if home is None or away is None:
        return None
    return "over" if (home + away) > 2.5 else "under"


def _load_dotenv_local(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        import os
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def run_audit(
    predictions_path: str = "data/predictions/2026-08-21-predictions.json",
    output_dir: str = "data/live/audit",
    api_date: str | None = None,
    use_api_sports: bool = True,
    use_football_data: bool = True,
    use_fdccouk: bool = False,
    fdccouk_season: str = "2324",
    fdccouk_league: str = "T1",
) -> dict:
    preds = json.loads(Path(predictions_path).expanduser().read_text(encoding="utf-8"))
    _load_dotenv_local()
    matches = preds["predictions"] if isinstance(preds, dict) else preds

    # gerçek sonuçları topla
    real_rows: list[dict] = []
    sources_used = []
    if use_api_sports:
        try:
            if api_date:
                real_rows += [r.to_dict() for r in fetch_api_sports(api_date)]
                sources_used.append("api-sports")
        except Exception as exc:
            sources_used.append(f"api-sports-err:{exc}")
    if use_football_data:
        try:
            real_rows += [r.to_dict() for r in fetch_football_data()]
            sources_used.append("football-data.org")
        except Exception as exc:
            sources_used.append(f"football-data-err:{exc}")
    if use_fdccouk:
        try:
            real_rows += fetch_fdccouk_results(fdccouk_season, fdccouk_league)
            sources_used.append(f"football-data.co.uk:{fdccouk_season}-{fdccouk_league}")
        except Exception as exc:
            sources_used.append(f"fdccouk-err:{exc}")

    audit_lines = []
    total_1x2 = total_ou = hit_1x2 = hit_ou = 0
    for m in matches:
        real = _match_real(real_rows, m["home_team"], m["away_team"])
        real_result = _result_from_score(real.get("home_goals") if real else None, real.get("away_goals") if real else None)
        real_ou = _ou_from_score(real.get("home_goals") if real else None, real.get("away_goals") if real else None)
        pred_1x2 = m.get("predicted_1x2")
        pred_ou = m.get("predicted_ou")
        h1 = (real_result == pred_1x2) if real_result else None
        ho = (real_ou == pred_ou) if real_ou else None
        if h1 is not None:
            total_1x2 += 1; hit_1x2 += int(h1)
        if ho is not None:
            total_ou += 1; hit_ou += int(ho)
        audit_lines.append({
            "match_index": m.get("match_index"),
            "home_team": m["home_team"], "away_team": m["away_team"],
            "predicted_1x2": pred_1x2, "actual_1x2": real_result,
            "predicted_ou": pred_ou, "actual_ou": real_ou,
            "hit_1x2": h1, "hit_ou": ho,
            "real_source": real.get("source") if real else None,
            "home_goals": real.get("home_goals") if real else None,
            "away_goals": real.get("away_goals") if real else None,
        })

    out_dir = Path(output_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_path = out_dir / f"audit_{stamp}.jsonl"
    with audit_path.open("w", encoding="utf-8") as fh:
        for line in audit_lines:
            fh.write(json.dumps(line, ensure_ascii=False) + "\n")

    summary = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "predictions_path": predictions_path,
        "sources_used": sources_used,
        "matches_total": len(matches),
        "matches_with_result": total_1x2,
        "matches_with_ou": total_ou,
        "hit_1x2": hit_1x2, "accuracy_1x2": round(hit_1x2 / total_1x2, 3) if total_1x2 else None,
        "hit_ou": hit_ou, "accuracy_ou": round(hit_ou / total_ou, 3) if total_ou else None,
        "details": audit_lines,
    }
    summary_path = out_dir / f"summary_{stamp}.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", default="data/predictions/2026-08-21-predictions.json")
    ap.add_argument("--date", default=None, help="API-Sports tarih filtresi (YYYY-MM-DD)")
    ap.add_argument("--no-api", action="store_true")
    args = ap.parse_args()
    s = run_audit(args.predictions, api_date=args.date, use_api_sports=not args.no_api)
    print(f"Audit: {s['matches_with_result']}/{s['matches_total']} maçta sonuç var")
    print(f"1X2 isabet: {s['hit_1x2']}/{s['matches_with_result']} = {s['accuracy_1x2']}")
    if s["matches_with_ou"]:
        print(f"Alt/Üst isabet: {s['hit_ou']}/{s['matches_with_ou']} = {s['accuracy_ou']}")
    print("Kaynaklar:", s["sources_used"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
