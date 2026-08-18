# GitHub Kaynakları Benimseme Raporu — 2026-08-18

## Football-Data.co.uk

Durum: Ana tarihsel sonuç/oran katmanı olarak aktif.

- `src/sportoto/real_training.py` gerçek tarihsel sonuçları topluyor.
- `src/sportoto/odds.py` kapanış 1X2 ve Alt/Üst oranlarını okuyor.
- Walk-forward eğitimlerde kullanılan parquet setleri bu katmandan geliyor.

## Transfermarkt Datasets

Durum: Leakage-safe özellik katmanı ve canlı tahmin vektörü aktif; ana varsayılan model henüz otomatik olarak değiştirilmedi.

- Kaynak dosya: `data/raw/transfermarkt/transfers.csv.gz`
- Uygulama: `src/sportoto/transfer_features.py`
- Eğitim entegrasyonu: `scripts/train_real_walkforward.py --transfer-csv ...`
- Özellikler: son 365 günde giriş/çıkış sayısı ve net transfer bedeli.
- Her maçta yalnızca `transfer_date < kickoff` kayıtları kullanılıyor.

Walk-forward karşılaştırması (Super Lig, 1.370 maç, 5 rolling fold, 870 test maçı):

- Temel model: mean accuracy 0.5006, mean lift 0.0463, mean Brier 0.2077, mean log-loss 1.0464
- Transfer tüm özellikler (sayı + ücret): mean accuracy 0.4977, mean lift 0.0435, mean Brier 0.2136, mean log-loss 1.0843 -> terfi edilmedi
- Transfer yalnızca giriş/çıkış sayıları: mean accuracy 0.5096, mean lift 0.0553, mean Brier 0.2100, mean log-loss 1.0614; 5/5 fold pozitif lift -> **SHIP**

Terfi edilen model: `data/models/real_superlig_transfer_counts_rolling.joblib`. Canlı tahmin vektörü de `transfer_mode=counts` ile bu şemayı kullanıyor. Transfer ücret özellikleri kalibrasyonu bozduğu için ana modele alınmadı.

## StatsBomb Open Data

Durum: Ayrı gelişmiş analitik katmanı olarak doğrulandı.

- Parser: `src/sportoto/advanced_analytics.py`
- Doğrulanan örnek: event payload 3.589 olay, 33 şut.
- Çıktı: `data/analysis/statsbomb-8650.json`
- StatsBomb tüm Spor Toto liglerini kapsamadığı için ana 1/X/2 modeline zorla eklenmedi.

## Transfermarkt web haber adapteri / Engsoccerdata

- Transfermarkt haber/manager sinyali adapteri mevcut; tarihsel ana feature olarak henüz kullanılmıyor.
- Engsoccerdata uzun dönem tarihsel bağlam için uygun; güncel Spor Toto ana modeline eklenmedi.

## Terfi kuralı

Hiçbir yeni kaynak ana canlı tahmin modeline yalnızca mevcut olması nedeniyle eklenmez. Zaman sızıntısız walk-forward lift, kalibrasyon ve kapsam kontrolü gerekir.
