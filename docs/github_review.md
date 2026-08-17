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

## public-apis (github.com/public-apis/public-apis) triyajı — 2026-08-17
Spor/odds kategorisi tarandı (README 235KB).

Spor/odds API'leri ve durumları:
- **Bet Better** (betbetter.world/api): BEDAVA, NO KEY, CC BY 4.0. Model kazanma
  olasılığı + fair odds (9 spor). Futbol: /soccer/{league}/ (EPL, La Liga, Serie A,
  Bundesliga, Ligue 1, MLS, WC). → BİZİM MODELE ÇAPRAZ KONTROL kaynağı.
  DURUM: Şu an futbol sezonu kapalı (sadece tenis veriyor); 403 (Cloudflare) —
  adapter hazır (fetch_betbetter) ama sezon açılınca test edilecek.
- **Football-Data** (football-data.org): ZATEN KULLANIYORUZ (football-data.co.uk
  ile aynı veri; oran ücretli, sonuçlar ücretsiz).
- **Oddsmagnet** (data.oddsmagnet.com): Bedava oran geçmişi (UK) → 403 (bot block),
  erişilemez.
- **Sportmonks Football** (docs.sportmonks.com): score/schedule/stats/history →
  API KEY gerekir (football-data.org gibi).

SONUÇ: public-apis listesinden şu an Spor Toto'ya YENİ gerçek entegrasyon kazancı
sınırlı. Bet Better (sezon açılınca çapraz kontrol için değerli) adapter olarak
hazırlandı; diğerleri ya zaten var ya erişilemez ya key gerektiriyor.

Not: Bet Better 403 aldığı için fetch_betbetter() şu an boş/exception dönebilir;
Cloudflare bypass gerektirir (production'da kullanılmayacak kadar korumalı).
