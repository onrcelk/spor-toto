# Sprint 3 — Decision Stage

Decision stage deterministic olarak ensemble + risk policy'den option-set üretir.

```text
banko_allowed=true
  -> en yüksek olasılık: 1 / X / 2

banko_allowed=false
  -> top two: 1X / X2 / 12
  -> top three birbirine yakınsa: 1X2
```

Decision stage olasılıkları değiştirmez. Her karar kaydında:

- `selection`
- `primary`
- `secondary`
- `confidence`
- `banko`
- deterministic reasons
- probabilities

bulunur.

Risk yüksek diye ensemble olasılığı düşürülmez; yalnızca banko izni kapanır veya option-set genişler.

H15 optimizer henüz bu stage'e bağlanmadı. Decision stage'in görevi maç başına option-set üretmektir; kolon portföyü sonraki aşamadır.
