# Sprint 3 — Sport Toto Orchestration Workflow

İlk workflow dilimi Hermes çekirdeğine dokunmadan oluşturuldu.

## State

`WorkflowState` frozen dataclass olarak şu alanları taşır:

- fixtures
- research_decisions
- retrievals
- evidence
- data_quality
- model_predictions
- calibrated_predictions
- ensemble
- risk
- decisions
- coupon
- audit
- stage_history

`advance()` yeni state üretir; önceki state sessizce değiştirilmez. Aynı stage ikinci kez uygulanamaz.

## Workflow

```python
workflow = SportTotoWorkflow(run_id, fixtures, research_tool_registry)
state = workflow.run_until_research()
```

İlk aktif aşamalar:

```text
fixture_validation
research_decision
research_collection
```

Prediction, calibration, ensemble, risk, journal ve coupon aşamaları için henüz sonuç uydurulmaz; kontrollü stage placeholder'ları bulunur.

## Sınır

Workflow doğrudan Odds/Squad/News adapterlarını bilmez. Sadece `ResearchToolRegistry` üzerinden kategori ister. Hermes-facing entegrasyon daha sonraki aşamadır.
