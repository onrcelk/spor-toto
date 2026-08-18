# Sprint 2 — Squad Adapter

Squad tarafı Odds Adapter'dan ayrı provider/adapter katmanlarıyla eklendi.

## Kapsam

İlk sürüm yalnızca evidence üretir:

- player availability
- injury
- suspension
- expected lineup
- goalkeeper availability

Oyuncu bilgisinden maç sonucu, gol katkısı veya xG cezası çıkarmaz.

## Durumlar

```text
confirmed: fresh + verified claim
uncertain: claim var ama verified/fresh değil
conflict: farklı fresh verified kaynaklar farklı claim veriyor
missing/timeout: retrieval sonucu; football evidence değildir
```

## Kullanım

```python
from sportoto.adapter_contracts import AdapterRegistry
from sportoto.squad_adapter import SquadAdapter
from sportoto.squad_providers import StaticSquadProvider

registry = AdapterRegistry()
registry.register(SquadAdapter(StaticSquadProvider(rows, source="official")))
result = registry.retrieve(["squad"], "M04")[0]
```

## Odds + Squad runner

`run_research.py` opsiyonel `--squad` fixture'ı ile iki adapterı aynı journal akışında çalıştırabilir. Odds sayımları Squad sonuçlarından bağımsız kalır; evidence ve risk alanları ortak journal'a eklenir.
