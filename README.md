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
