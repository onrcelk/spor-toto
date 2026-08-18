# Sprint 2 — Odds Adapter

`src/sportoto/odds_adapter.py` provider-neutral odds adapterı eklendi.

## Sorumluluk

Adapter yalnızca şunları yapar:

```text
raw odds
  -> validation
  -> raw implied probability
  -> overround
  -> vig-removed market probability
  -> odds evidence
```

Tahmin veya "oynanmalı" kararı üretmez.

## Validation

- 1/X/2 üçlüsü zorunlu
- Oranlar finite ve `> 1` olmalı
- Eksik oran tahminle doldurulmaz
- Complete retrieval ile incomplete market evidence ayrıdır
- Retrieval failure evidence üretmez
- Duplicate match satırı parse error olur
- Freshness bilinmiyorsa evidence `verified=false` kalır

## Uçtan uca static odds araştırması

```bash
uv run python scripts/run_research.py \
  --journal data/analysis/decision_journal_2026W34.jsonl \
  --odds data/live/odds_2026-08-21_telegram_visible_tr.json \
  --output data/analysis/decision_journal_2026W34_odds_e2e.jsonl
```

Mevcut 15 maçlık fixture ile deterministik çıktı:

```text
matches=15
odds_found=8
market_available=8
verified=0
research_required=7
```

`verified=0`, Telegram kaydında freshness/timestamp bulunmadığı için beklenen sonuçtur. `research_required=7`, odds retrieval bulunamayan yedi maçtır; mevcut sekiz maç ise ayrıca doğrulanmamış freshness riski taşır.


```python
from sportoto.adapter_contracts import AdapterRegistry
from sportoto.odds_adapter import OddsAdapter
from sportoto.odds_providers import TelegramStaticOddsProvider

registry = AdapterRegistry()
registry.register(OddsAdapter(TelegramStaticOddsProvider(rows)))
results = registry.retrieve(["odds"], "M04")
```

Mevcut 8 maçlık Telegram oran kaydı static provider olarak kullanılabilir; kaynağın timestamp/freshness bilgisi yoksa validator oranı doğrulanmış saymaz.
