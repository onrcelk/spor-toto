# Sprint 3 — H15 Coupon V1

H15 optimizer karar katmanının tüketicisidir; prediction, calibration, ensemble, risk veya decision değiştirmez.

```text
Decision
  ↓
Option Set Builder
  ↓
Scenario Generator
  ↓
Filter Engine
  ↓
Coupon State
```

İlk sürümde portfolio optimization yoktur. Tüm geçerli senaryolar üretilir, filtreler sırayla uygulanır ve her filtre için before/after/removed audit tutulur.

```python
state = workflow.run_coupon(
    state,
    filters=[("max_draws", lambda scenario: sum(v == "X" for v in scenario.values()) <= 4)],
    actual=None,
)
```

Coupon state:

- option_sets
- scenario_count
- filters
- filtered_scenario_count
- selected_scenarios
- boş portfolio hedefi
- actual preservation audit

Gerçek sonuç verilirse `actual_in_all_scenarios`, `actual_in_filtered` ve ilk eliminasyon filtresi kaydedilir. Bu katman model tahmini değildir.

Not: Mevcut legacy `sportoto.coupon` API'si korunmuştur; yeni workflow H15 V1 implementasyonu `sportoto.h15` modülündedir.
