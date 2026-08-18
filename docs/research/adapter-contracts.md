# Sprint 2 — Adapter Contract Layer

Gerçek provider çağrılarını bağlamadan önce ortak sözleşme sabitlendi.

## Retrieval sonucu ve evidence ayrımı

`src/sportoto/adapter_contracts.py`:

- `success`
- `timeout`
- `unavailable`
- `parse_error`
- `rate_limited`

Başarısız retrieval sonucu evidence içeremez. Erişilemeyen kaynak ile doğrulanmamış iddia aynı kayıt değildir.

## Ortak adapter kategorileri

- `odds`
- `squad`
- `news`

`AdapterRegistry` yalnızca Research Decision tarafından istenen kategorileri çağırır. Kayıtlı olmayan adapter otomatik olarak `unavailable / adapter_not_registered` döner; rastgele tool çağrısı yapılmaz.

## Conflict

Aynı kategoride fresh ve verified kaynaklar farklı claim bildirirse validator:

```text
agreement = conflicted
verified = false
risk flag = <category>_source_conflict
banko_allowed = false
```

Kaynak sayısı tek başına çoğunluk kararı üretmez; kaynak güven skorları korunur ve ağırlıklı çözüm sonraki sprintte ele alınır.
