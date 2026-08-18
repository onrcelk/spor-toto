# Sprint 3 — Ensemble Stage

Ensemble stage mevcut `ensemble_probabilities()` motorunu workflow'a bağlar; yeni ağırlık optimizasyonu veya model eğitimi yapmaz.

## Sözleşme

```text
calibrated_predictions
        ↓
existing ensemble engine
        ↓
WorkflowState.ensemble
```

Calibration yoksa stage fail olur; raw `model_predictions` üzerinden sessiz fallback yapılmaz.

Her ensemble kaydı:

- `match_id`
- calibrated model input
- market input (varsa)
- home/away xG input
- output 1/X/2

State metadata:

```json
{
  "method": "existing_ensemble",
  "weights": {"model": 0.55, "market": 0.30, "dixon": 0.15},
  "input": "calibrated_predictions",
  "output": "ensemble"
}
```

Eksik xG veya eşleşmeyen maç ID'si doldurulmaz; stage fail olur. Mevcut 15 maçlık artifact ile ensemble çıktısı 15 satır olarak doğrulandı.
