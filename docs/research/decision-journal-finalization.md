# Sprint 3 — Decision Journal Finalization

`WorkflowState` source of truth, Decision Journal audit projection olarak uygulanmıştır.

```text
WorkflowState
  prediction + calibration + ensemble + risk + decision
        ↓
project_state()
        ↓
idempotent decision_journal.jsonl
```

Finalizer hiçbir olasılığı, riski veya kararı yeniden hesaplamaz.

Her kayıtta:

- raw ve calibrated prediction
- ensemble output + metadata
- risk level/confidence/score/flags/banko
- decision selection/primary/secondary/reasons
- evidence ID referansları
- stage history
- boş post-match alanları

bulunur.

Coverage bütün stage'lerde fixture ID'leriyle birebir aynı değilse finalizer fail olur; kısmi journal yazılmaz.

Record ID deterministiktir:

```text
<run_id>:<match_id>:v1
```

Aynı state iki kez yazılsa dahi writer duplicate record üretmez.
