# Sprint 3 — Calibration Stage

Calibration stage raw model olasılıklarını önceden fit edilmiş bir `Calibrator` üzerinden dönüştürür. Calibration evaluator metrikleri ayrı tutulur.

## İlk implementasyon

`IdentityCalibrator` açık fallback'tir:

```text
raw == calibrated
method = identity
```

Bu, kalibrasyon yapıldığı iddiası değildir; yalnızca production workflow sözleşmesini ve invariantları doğrular. Isotonic/Platt gibi calibratorlar geçmiş holdout verisiyle fit edilip frozen olarak bağlanacaktır.

## State geçişi

```python
state = workflow.run_prediction(state, prediction_artifact)
state = workflow.run_calibration(state, IdentityCalibrator(version="identity-test"))
```

`calibrated_predictions` her maç için:

- `match_id`
- `raw`
- `calibrated`

taşır. Ayrıca `calibration_metadata` içinde method, version, fitted_until, input ve output tutulur.

## Güvenlik

- Model prediction yoksa stage fail olur.
- Probability key/bounds/sum geçersizse stage fail olur.
- Aynı stage ikinci kez uygulanamaz.
- Input state değiştirilmez.
- Aynı 15 maçla calibrator fit edilmez.

Brier, log-loss ve reliability metrikleri `sportoto.calibration` içinde evaluator fonksiyonları olarak kalır; production stage'in kararını değiştirmez.
