# Spor Toto Ön Maç Analiz Şablonu

Her maç ana kupon ve Hedef15 filtreleri hazırlan **madan önce** doldurulur.

| Alan | Veri | Kaynak | Zaman | Güven | Etki |
|---|---|---|---|---|---|
| Son 5-10 maç |  |  |  |  |  |
| Atılan/yenen gol |  |  |  |  |  |
| İç saha/deplasman |  |  |  |  |  |
| İkili rekabet |  |  |  |  |  |
| Opta Factleri |  | Maçkolik/Opta |  |  |  |
| Sakat/cezalı |  |  |  |  |  |
| Beklenen 11 |  |  |  |  |  |
| Fikstür yorgunluğu |  |  |  |  |  |
| xG / xGA |  |  |  |  |  |
| Şut/isabetli şut |  |  |  |  |  |
| Taktik eşleşme |  |  |  |  |  |
| Motivasyon |  |  |  |  |  |
| Hakem |  |  |  |  |  |
| Hava/saha |  |  |  |  |  |

## Sonuç kararı

- Ana yön: `1 / X / 2`
- Hedef15 tercihi: `banko / çifte / kapalı`
- Sürpriz beklenen maç: `evet / hayır`
- Ters sürpriz adayı: `evet / hayır`
- Risk seviyesi: `düşük / orta / yüksek`
- Kararı değiştirecek eksik bilgi:

## Kurallar

- Opta Factleri maç başlamadan önce kullanılır.
- Opta Factleri garanti değildir; bağlam kanıtıdır.
- xG/xGA yoksa tahmin edilmez.
- Eksik kadro veya hakem bilgisi kesin varsayım olarak yazılmaz.
- Tek bir metrikle banko verilmez.
- Ana kupon kararı ve Hedef15 filtre kararı ayrı tutulur.
