# Sprint 2 — News Adapter & Generic Research Runner

News adapterı maç tahmini üretmez; yalnızca normalize claim üretir.

Desteklenen claim türleri:

- `lineup_intent`
- `injury_news`
- `suspension_news`
- `coach_change`
- `motivation_context`
- `rotation`
- `disciplinary_risk`

Örnek claim:

```json
{
  "type": "rotation",
  "value": "rotation_possible",
  "subject": "home",
  "freshness": "fresh",
  "verified": false
}
```

Geçersiz claimler evidence olarak üretilmez. Unverified/freshness bilinmeyen claimler kaydedilir fakat banko kararını engeller. Farklı fresh verified claimler validator tarafından `conflicted` olarak işaretlenir; majority vote uygulanmaz.

## Generic runner

`run_research.py` artık adapter özel `if/elif` zinciri yerine kategori listesiyle çalışır. Opsiyonel fixture'lar:

```bash
uv run python scripts/run_research.py \
  --journal JOURNAL.jsonl \
  --odds ODDS.json \
  --squad SQUAD.json \
  --news NEWS.json \
  --output RESEARCHED.jsonl
```

Araştırma bütçesi `AdapterRegistry` context'iyle korunur:

```python
{"max_attempts": {"odds": 1, "squad": 2, "news": 2}}
```

Bütçe aşılırsa `research_exhausted` döner ve evidence üretilmez.
