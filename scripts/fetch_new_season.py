"""Download the latest finished Super Lig season (2425 = 2025-26) from
football-data.co.uk (FREE, no key) and merge it into the existing
API-Sports 2022-2024 frame, producing a unified 2022-2026 dataset.

The existing file data/live/api_sports_superlig_2022_2024.json has raw records
with keys: match_id, home_team, away_team, kickoff_iso, home_goals, away_goals,
league, season. We normalize the football-data.co.uk CSV into the same shape and
append, deduping on (home_team, away_team, kickoff_iso).
"""
from __future__ import annotations

import csv
import io
import json
import urllib.request
from datetime import datetime
from pathlib import Path

EXISTING = Path("data/live/api_sports_superlig_2022_2024.json")
OUT = Path("data/live/api_sports_superlig_2022_2026.json")
SEASON_CSV = "https://www.football-data.co.uk/mmz4281/2425/T1.csv"


def _norm_month(d: str) -> str:
    # football-data.co.uk Date like 12/08/2025 -> 2025-08-12
    try:
        return datetime.strptime(d.strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return d.strip()


def download_2425() -> list[dict]:
    with urllib.request.urlopen(SEASON_CSV, timeout=30) as resp:
        text = resp.read().decode("utf-8", "replace")
    reader = csv.DictReader(io.StringIO(text))
    out = []
    for i, row in enumerate(reader):
        hg = row.get("FTHG"); ag = row.get("FTAG")
        if hg is None or ag is None or hg.strip() == "" or ag.strip() == "":
            continue
        try:
            hg_i = int(hg); ag_i = int(ag)
        except ValueError:
            continue
        date = _norm_month(row.get("Date", ""))
        out.append({
            "match_id": f"fdccouk-2425-T1-{i}",
            "home_team": row.get("HomeTeam", "").strip(),
            "away_team": row.get("AwayTeam", "").strip(),
            "kickoff_iso": f"{date}T00:00:00+00:00",
            "home_goals": hg_i,
            "away_goals": ag_i,
            "league": "Super Lig",
            "season": "2025-26",
        })
    return out


def main() -> int:
    existing = json.loads(EXISTING.read_text(encoding="utf-8"))
    print(f"Mevcut veri: {len(existing)} maç (2022-2024)")
    new_rows = download_2425()
    print(f"Yeni 2425 T1: {len(new_rows)} maç indirildi")

    # dedup on (home, away, date)
    seen = {(r["home_team"], r["away_team"], r["kickoff_iso"][:10]) for r in existing}
    added = 0
    for r in new_rows:
        key = (r["home_team"], r["away_team"], r["kickoff_iso"][:10])
        if key in seen:
            continue
        existing.append(r)
        seen.add(key)
        added += 1
    print(f"Eklendi: {added} (tekrar eden {len(new_rows) - added} atlandı)")

    # sort by date
    existing.sort(key=lambda r: r["kickoff_iso"])
    OUT.write_text(json.dumps(existing, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Birleşik veri: {len(existing)} maç -> {OUT}")
    # season span
    seasons = {}
    for r in existing:
        seasons[r.get("season", "?")] = seasons.get(r.get("season", "?"), 0) + 1
    print("Sezon dağılımı:", seasons)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
