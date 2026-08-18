# Sprint 2 — Research Orchestration & Evidence Validation

Sprint 2'nin ilk dilimi tamamlandı.

## Research Decision

`decide_research()` mevcut veri kalitesini inceleyip araştırma gerekip gerekmediğini belirler.

Tetikleyiciler:

- Eksik oran: `odds`
- Eksik ilk 11/kadro: `squad`
- Eksik haber: `news`
- Stale kaynak: ilgili kategori
- Kaynak çatışması: yüksek öncelik
- Düşük data quality: genel doğrulama

Araştırma gerekmiyorsa `priority=none` döner; Hermes gereksiz tool çağrısı yapmaz.

## Evidence Store

`Evidence` kaydı:

- `evidence_id`
- `match_id`
- `claim`
- `category`
- `source` / `source_url`
- `source_reliability`
- `published_at` / `retrieved_at`
- `freshness`
- `verified`

`evidence_id`, claim ve kaynak içeriğinden deterministik hash ile üretilir.

## Source Validator

İki veya daha fazla farklı kaynaktan gelen, fresh ve verified kayıtlar `confirmed` olur. Tek kaynak `single_source`, doğrulanmamış kayıt `unverified` kalır.

Doğrulanmamış evidence:

- Journal'a referans olarak eklenir.
- Risk flag üretir.
- `banko_allowed=false` yapar.

## Journal entegrasyonu

```bash
uv run python scripts/apply_evidence_to_journal.py \
  --journal data/analysis/decision_journal_2026W34.jsonl \
  --evidence data/analysis/evidence_2026W34.jsonl \
  --output data/analysis/decision_journal_2026W34_researched.jsonl
```

Bu dilim gerçek web tool çağrısı yapmaz; araştırma kararını ve evidence doğrulama sözleşmesini sağlar. Squad/News/Odds adapterleri bir sonraki dilimde bu sözleşmeye bağlanacaktır.
