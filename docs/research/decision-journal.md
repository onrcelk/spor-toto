# Sport Toto Decision Journal

İlk Hermes orchestration sprinti tamamlandı.

## Kayıt katmanı

`src/sportoto/decision_journal.py` her maç için şu katmanları append-only JSONL kaydeder:

- fixture
- data_quality / cold_start / missing_fields
- source_reliability
- model_signals
- raw ve calibrated probabilities
- risk flags / banko_allowed
- decision / reasons
- coupon state
- post_match actual/hit/error_type

## Üretim

Ensemble çıktısından journal üretmek için:

```bash
uv run python scripts/build_decision_journal.py \
  --ensemble data/analysis/2026-08-21-ensemble-report.json \
  --output data/analysis/decision_journal_2026W34.jsonl \
  --run-id 2026W34
```

Kayıtlar LLM tarafından uydurulmaz; model ve piyasa sinyalleri kaynak dosyalarından taşınır. Eksik oranlar `market_available=false`, risk `high` ve `missing_market_odds` olarak kalır.

## Maç sonrası

`update_post_match` gerçek `1/X/2` sonucu ile hit/miss ve error type ekler. Tek maçtan model ağırlığı değiştirilmez; haftalık/rolling değerlendirme gerekir.
