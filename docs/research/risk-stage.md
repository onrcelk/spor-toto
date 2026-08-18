# Sprint 3 — Risk Stage

Risk stage ensemble olasılıklarını değiştirmez; yalnızca karar güveni ve banko izni üretir.

## Girdiler

- Data quality
- Source conflict
- Squad uncertainty
- Market availability
- Model disagreement
- Cold start
- Research exhausted

## Çıktı

Her maç için:

- `risk_level`: low / medium / high
- `confidence`: high / medium / low
- `risk_score`: karar riski metriği; probability değildir
- `flags`
- `factors`
- `banko_allowed`

Kritik flag'ler (`source_conflict`, `research_exhausted`) bankoyu kapatır. Risk stage ensemble/model/calibrated olasılıklarını değiştirmez.

İlk eşikler:

```text
model disagreement < .08   low
.08–.15                     medium
> .15                       high
```

Data quality, eksik market ve squad uncertainty medium seviyeye çıkarır; kritik conflict/exhaustion high seviyedir. Ağırlıklar ve eşikler henüz optimize edilmemiştir.
