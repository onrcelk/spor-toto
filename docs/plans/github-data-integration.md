# GitHub Veri Kaynakları Entegrasyonu Planı

Amaç: Açık veri kaynaklarını mevcut Spor Toto pipeline'ına kanıtlı, zaman sızıntısız ve rolü ayrılmış şekilde bağlamak.

Sıra:
1. Football-Data.co.uk sonuç/oran katmanını doğrula; mevcut eğitim kaynağını sabitle.
2. Transfermarkt dataset/transfer sinyallerini tarih damgalı takım-sezon özelliklerine dönüştür; hedef maçtan sonra oluşan bilgiyi feature'a sokma.
3. StatsBomb'u yalnızca kapsadığı turnuvalarda ayrı xG/şut gelişmiş katmanı olarak bağla; eksik xA/PPDA'yı doldurma.
4. Her katmanı walk-forward backtest ile baseline'a karşı ölç; lift yoksa ana modele alma.
5. Rapor, kaynak provenance, test ve Git durumunu doğrula.

Kabul kriterleri:
- Her kaynak için provider, gözlem zamanı ve kapsam kaydı mevcut.
- Tarih parse hatası veya NaT eğitimde sessizce kalmıyor.
- Ana 1/X/2 modelinde yeni özelliklerin katkısı out-of-sample ölçülüyor.
- Tüm testler geçiyor; zayıf veya kapsam dışı kaynak ana modele zorla eklenmiyor.
