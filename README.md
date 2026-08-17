# Sportoto
Spor toto maç tahmini projesi.

## Çoklu kaynak veri çekimi

Read-only kaynak adaptörleri:

- API-Sports: canlı/fikstür verisi (`API_SPORTS_KEY`)
- football-data.org: fikstür ve final sonuç doğrulaması (`FOOTBALL_DATA_API_TOKEN`)
- Open Football: ham GitHub JSON tarihsel veri, anahtarsız

Yerel anahtarlar yalnızca `.env` dosyasından okunur; `.env` Git tarafından ignore edilir.

Örnek komut:

```bash
uv run python -m sportoto.cli refresh-sources \
  --date 2026-08-17 \
  --openfootball-url https://raw.githubusercontent.com/openfootball/football.json/master/2015-16/en.1.json \
  --output data/live/multi_source/2026-08-17.json
```

Çıktı her kaynağın `count`, normalize maç kayıtları, kaynak kimliği, durum, sonuç ve Alt/Üst 2.5 alanlarını içerir. API anahtarları rapora yazılmaz.

## Gelişmiş analitik

StatsBomb Open Data olay JSON'larını parse etmek için:

```bash
uv run python -m sportoto.cli advanced-statsbomb \
  --url https://raw.githubusercontent.com/statsbomb/open-data/master/data/events/8650.json \
  --output data/analysis/statsbomb-8650.json
```

Çıktı; takım bazında StatsBomb xG toplamı, şut koordinatları, şut sonucu, freeze-frame sayısı, açıkça işaretlenmiş key pass ve defansif aksiyonları içerir. StatsBomb payload'ında doğrudan bulunmayan xA ve exact PPDA boş bırakılır; proxy metrikler resmi xA/PPDA diye etiketlenmez. StatsBomb verisi araştırma/analitik koşulları ve kaynak gösterimiyle kullanılmalıdır.

Leakage-safe xG rolling ve Poisson backtest:

```bash
uv run python -m sportoto.cli advanced-backtest \
  --input data/advanced_match_rows.json \
  --min-history 3 \
  --output data/analysis/advanced-backtest.json
```

Girdi satırları tarih, takım, gol, xG, xA ve şut alanlarını içerir. Özellikler her maçtan önceki maçlarla hesaplanır; hedef maçın kendi xG/golü feature üretimine girmez. Sonuç raporu 1/X/2 ve Alt/Üst 2.5 doğruluğunu ayrı verir.

## Model güvenilirliği ve audit katmanları

- `sportoto.market`: implied probability, vig removal, EV ve closing-line delta.
- `sportoto.dixon_coles`: xG'den ortak 1/X/2, Alt/Üst, BTTS ve doğru skor posterioru.
- `sportoto.calibration`: multiclass Brier, log-loss ve reliability bins.
- `sportoto.identity`: provider takım adı/alias canonicalization.
- `sportoto.evidence`: kaynaklı, zaman damgalı ve etkisi etiketli kanıt paketleri.
- `sportoto.availability`: doğrulanmış/beklenen kadro belirsizliğini xG'ye sınırlı ağırlık olarak yansıtır.

Bu modüller bağımsız ve test edilebilirdir; eksik xA/PPDA veya sakatlık verisi varsayımla doldurulmaz.
