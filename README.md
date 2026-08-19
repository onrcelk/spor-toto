# Sportoto — Hedef15 Tahmin & Filtre Sistemi

[![Tests](https://img.shields.io/badge/tests-168-passing-brightgreen)](tests/)
[![Python](https://img.shields.io/badge/python-3.11-blue)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

Spor Toto (Türk bahis sistemi) için **deterministik, kaynak-temelli** bir tahmin ve Hedef15 filtreleme motoru.
Model tabanlı tahmin yerine, **gerçek tarihsel veri + çok-kaynaklı oran teyidi + YouTube dokümante edilmiş filtre semantiği** kullanır.

## 🎯 Özellikler

- **Walk-forward model eğitimi** (leak-free ELO, zaman-sıralı doğrulama)
- **4 bağımsız oran kaynağı**: kullanıcı görseli, The Odds API, Flashscore, manuel
- **Hedef15 filtre sistemi**: 15 filtre (sürpriz, beraberlik, ters sürpriz, ardışıklık, segment bazlı)
- **Audit pipeline**: oynanmış kuponu gerçek sonuçlarla kıyaslar
- **Streamlit dashboard**: tahmin + oran + filtre görselleştirme

## 📊 Model Doğrulama (sports-betting ile karşılaştırmalı)

| Model | Accuracy | Lift |
|---|---|---|
| Baseline (majority) | 0.4526 | — |
| **Bizim GB** | 0.4927 | **+0.0401** |
| sports-betting Logit | 0.5073 | +0.0547 |

Kaynak: `data/analysis/model_comparison_sportsbet.json` (Süper Lig 1370 maç)

## 🏗️ Proje Yapısı

```
src/sportoto/
  features.py          # Leak-free ELO, feature mühendisliği
  train.py             # Walk-forward eğitim
  audit.py             # Oynanmış kupon audit'i
  coupon.py            # Hedef15 filtre uygulama
  dashboard/app.py     # Streamlit görselleştirme
  mcp_server.py        # Hermes MCP entegrasyonu
data/
  predictions/         # Haftalık tahminler
  live/                # Gerçek sonuçlar, oranlar, audit
  models/              # Eğitilmiş modeller
docs/research/         # Hedef15 Filtre Spesifikasyonu
```

## 🚀 Kullanım

```bash
# Sanal ortam
uv sync

# Walk-forward model eğitimi
python scripts/train_real_walkforward.py

# 21 Ağustos tahmini (oranlarla)
cat data/predictions/2026-08-21-predictions.json

# Dashboard
streamlit run src/sportoto/dashboard/app.py
```

## 📋 Hedef15 Filtre Spesifikasyonu

Strict source-first: YouTube (Ozan Bey) altyazılarından çıkarılmış 15 filtre.
Tam spesifikasyon: `docs/research/hedef15-filter-spec-v1.md`

## ⚠️ Yasal Uyarı

Bu araç **yalnızca araştırma/eğitim** amaçlıdır. Gerçek bahis oynatmaz, oran sağlamaz.
Tüm oranlar kamuya açık kaynaklardan toplanır.

## 📄 Lisans

MIT
