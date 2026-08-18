# Sprint 4.1 — Hermes Domain Interface

`SportTotoService` Hermes-facing tek yüksek seviye giriş noktasıdır. İç adapter, calibration, risk ve H15 modülleri dışarı sızdırılmaz.

```python
service = SportTotoService(tool_registry)
result = service.run(
    run_id="2026W34",
    fixtures=fixtures,
    prediction_artifact="predictions.json",
    journal_path="decision_journal.jsonl",
)
```

## WorkflowResult

- `status`: `completed` / `failed`
- `fixture_count`
- `completed_stages`
- özet: high risk, banko/double/triple, scenario counts
- artifact yolları
- hata varsa `failed_stage` ve `error`

Hermes'in olasılık, risk veya karar override etmesi için interface bulunmaz.

## Gerçek 15 maç full E2E

Mevcut fixture ve prediction artifact ile tek çağrı sonucu:

```text
fixtures: 15
research decisions: 15
predictions: 15
calibrated: 15
ensemble: 15
risk: 15
decisions: 15
journal records: 15
h15 scenarios: 559872
filtered scenarios: 559872
status: completed
```

Portfolio optimization bu aşamada bilinçli olarak yoktur.
