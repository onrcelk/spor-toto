"""HATA ANALİZİ: 21 Ağu 15 maç tahminindeki sistemli hataların tespiti ve düzeltme
etkisinin gösterimi.

KÖK NEDENLER (predict_week.py eski sürümü):
1. İSİM EŞLEŞMEME: _team_aggregates / _h2h normalize_team_name KULLANMIYORDU.
   2025-26 SL takımları ("Erzurumspor FK", "Çaykur Rizespor A.Ş.") parquet'teki
   eski isimlerle ("Erzurum BB", "Rizespor") eşleşmedi -> sample_size=0 ->
   lig ortalaması fallback -> 7 SL maçının TAMAMI aynı olasılık (0.353/0.415/0.233)
   -> hepsi X tahmini (draw en yüksek). BU BÜYÜK BİR HATA.
2. GOL ORTALAMASI MANTIĞI: eski kod takımın sadece EV maçlarını filtreleyip
   yanlış gol ortalaması hesaplıyordu (ev/deplasman ayrımı bozuktu).

DÜZELTME:
- _team_aggregates: takımın EV+DEPLASMAN tüm maçını normalize_team_name ile
  eşleştirip genel gol/güç ortalaması hesaplar.
- _h2h: aynı şekilde normalize edilmiş eşleştirme.
- parquet'te hazır feature sütunları (home_goals_avg vb.) kullanılır (ham gol yok).

SONUÇ: 7 SL maçı artık farklı tahminler (1/2/X karışık), sample_size dolu (8/8),
form/xg takım bazlı değişiyor. Genel model maçları da etkilenmedi.
"""
from __future__ import annotations

import json


def main() -> int:
    d = json.load(open("data/predictions/2026-08-21-predictions_HYBRID.json", encoding="utf-8"))
    print("=== 21 Ağu 15 maç — DÜZELTİLMİŞ tahminler ===")
    print(f"{'M':>3} {'Ev':18} {'Deplasman':18} {'1X2':>4} {'sz_h/sz_a':>8} {'form_h/form_a':>14}")
    for p in d["predictions"]:
        f = p["features"]
        print(f"{p['match_index']:>3} {p['home_team'][:18]:18} {p['away_team'][:18]:18} "
              f"{p['predicted_1x2']:>4} {str(f['home_sample_size'])+'/'+str(f['away_sample_size']):>8} "
              f"{str(f['home_form_points'])+'/'+str(f['away_form_points']):>14}")
    # özet: kaç farklı tahmin
    from collections import Counter
    c = Counter(p["predicted_1x2"] for p in d["predictions"])
    print(f"\nTahmin dağılımı: {dict(c)} (eski bozuk sürümde 7 SL hepsi X'di)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
