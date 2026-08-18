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

## Adapter registry kullanımı

```python
from sportoto.adapter_contracts import AdapterRegistry
from sportoto.odds_adapter import StaticOddsAdapter

registry = AdapterRegistry()
registry.register(StaticOddsAdapter(rows, source="telegram_screenshot"))
results = registry.retrieve(["odds"], "M04")
```

Mevcut 8 maçlık Telegram oran kaydı static provider olarak kullanılabilir; kaynağın timestamp/freshness bilgisi yoksa validator oranı doğrulanmış saymaz.
