# GitHub Repo Triyaj Raporu (Spor Toto pipeline)

Kullanıcının verdiği 90 link (75 benzersiz) incelendi. Kategorizasyon ve
Spor Toto'ya (1X2 tahmin + ücretsiz oran + kupon stratejisi) gerçek katkı
değerlendirmesi aşağıda.

## Kategori dağılımı
- EDA / ödev / video-analiz (YOLO, FIFA WC, SQL): ~60 repo — işimize yaramaz.
- Tahmin modeli (aliAljaffer, ParthK7, seohyeoning, vishant-mehta, adriangonz,
  DanDom2019, Saf2004 vb.): bizim Dixon-Coles + GBM + ELO (acc 0.509) ile
  eşdeğer/zayıf; yeniden entegre etmeye değer değil.
- Bahis oranı analizi / lottery: 3 repo — EN DEĞERLİ.
- Web scraping (Ezee-Kits x6, ShubhankarRk): LİSANS/ToS RİSKİ — entegre edilmedi.

## En değerli bulunanlar (entegre edildi / fikir alındı)
1. **MoritzGoeckel/SoccerDataAnalysis** — "betting odds ↔ match outcome" analizi.
   LICENSE YOK (telif riski). Fikir: oran↔sonuç öğrenme. Bizim `odds.py` +
   `audit.py` ile zaten örtüşüyor; kod KOPYALANMADI.
2. **samarpreetxd/Soccer-Betting-Model** — MIT lisansı. Production-style
   training + backtesting + policy learning. Fikri (`value_backtest.py` ile
   aynı-sezon +EV backtest) bizim pipeline'a uyarlandı. ATIF: README'de.
   Verisi football-data.co.uk formatında (biz zaten `fetch_fdccouk` ile çekiyoruz).
3. **ParthK7/Soccer-Match-Outcome-Prediction-** — Featuretools otomatik feature.
   LICENSE YOK. Manuel feature'ımıza ek olarak denenebilir (ileride).

## Licans/ToS riski nedeniyle ENTEGRE EDİLMEMİŞ
- Ezee-Kits/SPORTYBET-WEB-SCRAPING, -/Bet9ja-Web-Scraper..., -/Bangbet-...,
  -/-Betbonanza..., -/PARIMATCH-WEB-SCRAPING: bahis sitelerinden scraping →
  site ToS ihlali riski. Kullanıcı tercihi: "3. taraf araçta lisans/şart denetimi".
- ShubhankarRk/Soccer-Web-Scraper: WhoScored scraping → benzer risk.
- Bu reposlar SADECE referans; kodları projeye dahil edilmedi.

## Ne yapıldı
- `src/sportoto/value_backtest.py`: aynı-sezon (2324 T1) gerçek kapanış oranı
  ile +EV flat-stake backtest. Sonuç: 109 bahis, +%3.81 ROI, %46.8 kazanma.
- CLI: `value-backtest` komutu.
- `fetch-odds --source fdccouk` (önceki oturum) ücretsiz oran kaynağı.

## İleride değerlendirilebilir
- Featuretools ile otomatik feature (ParthK7) → acc 0.509'u artırabilir.
- The Odds API ücretsiz 500 kredi/ay → canlı maç günü oranı için (kayıt gerekir).
