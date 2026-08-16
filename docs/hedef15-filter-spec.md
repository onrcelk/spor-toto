# Spor Toto Hedef15 Filtreleme Mantığı — Çıkarılmış Teknik Spesifikasyon

Kaynak: `Spor Toto Hedef15 Ozan Bey.zip` içindeki Türkçe altyazılar.

## 1. Temel kavramlar

Her maç için üç sonuç vardır: `1`, `X`, `2`.

Ana kupon, her maçta seçilen tercih tiplerinden oluşur:

- **Banko:** Tek sonuç. Kombinasyon içinde değişmez.
- **Çifte:** İki sonuç. Örnek: `1X`, `X2`, `12`.
- **Kapalı:** Üç sonuç. `1X2`.

Ana kombinasyon, banko/çifte/kapalı tercihlerinin kartezyen çarpımıdır.
Örnek:

```text
4 banko + 9 çifte + 2 kapalı
= 2^9 × 3^2
= 4.608 kolon
```

Buradaki kolonlar filtreleme öncesi aday kolonlardır.

## 2. Banko ve favori ayrımı

- **Banko sonucu**, kullanıcının o maç için sabitlediği sonuçtur.
- **Maç favorisi**, sistemdeki en yüksek oynanma yüzdesine göre belirlenen sonuçtur.
- Varsayılan olarak banko/favori aynı kabul edilir; ancak kullanıcı bankoyu değiştirebilir.
- Ters sürpriz hesabı bankoya değil, tanımlanan **maç favorisine** göre yapılmalıdır.
- Banko olarak sabitlenen maçlar filtrelerin değişken alanına dahil edilmez.

## 3. Sürpriz sınıfları

### 3.1. Normal sürpriz

Kullanıcının banko/favori sonucundan farklı olan her sonuç normal sürprizdir.

Özellikle:

- Banko `1`, sonuç `X` → normal sürpriz
- Banko `1`, sonuç `2` → ters sürpriz ve aynı zamanda sürpriz
- Banko `2`, sonuç `X` → normal sürpriz
- Banko `2`, sonuç `1` → ters sürpriz ve aynı zamanda sürpriz
- Banko `X`, sonuç `1` veya `2` → normal sürpriz

### 3.2. Ters sürpriz

Yalnızca şu iki durum ters sürprizdir:

- Favorisi/bankosu `1` olan maçın `2` bitmesi
- Favorisi/bankosu `2` olan maçın `1` bitmesi

Beraberlik hiçbir zaman ters sürpriz sayılmaz. Beraberlikler normal sürprizdir.

### 3.3. Sürpriz beklenen maçlar

Bir maçta çifte veya kapalı tercih varsa, o maçta sürpriz arandığı kabul edilir.

- Banko maçlar sürpriz beklenen maç grubuna girmez.
- Çifte ve kapalı maçlarda sonuç bankodan/favoriden farklıysa sürpriz sayılır.
- Ters sürpriz, normal sürprizin özel alt sınıfıdır.

## 4. Filtre sonucu ve garanti koşulu

Bir filtre, ana kombinasyondan yalnızca belirli koşulu sağlayan kolonları bırakır.

Örneğin seçilen bir grupta beklenen sürpriz sayısı `{2, 3, 4}` ise:

- Gerçek sonuç sayısı 2, 3 veya 4 ise filtre başarılıdır.
- Gerçek sonuç sayısı 1 veya 5 ise filtre başarısızdır.
- Filtre başarısız olursa özel sistemde 15 seviyesi korunmaz; sonuç bir alt dereceye düşebilir.

**Önemli:** Kullanılmayan filtreler sonuç değerlendirmesine dahil edilmez. Sadece kullanıcının seçtiği filtreler bağlayıcıdır.

## 5. Filtre türleri

### 5.1. Toplam beraberlik sayısı

Seçilen çifte/kapalı maç grubunda kaç maçın `X` biteceği filtrelenir.

Örnek:

```text
Beraberlik beklenen 4 maç
İzin verilen sayılar: 1, 2, 3
```

- 1–3 beraberlik → filtre başarılı
- 0 veya 4 beraberlik → filtre başarısız

### 5.2. Toplam sürpriz sayısı

Çifte ve kapalı maçlardan oluşan sürpriz beklenen grupta, favoriden farklı kaç sonuç geldiği filtrelenir.

Normal sürpriz ve ters sürpriz birlikte sayılır.

Örnek:

```text
11 maçta sürpriz aranıyor
İzin verilen toplam sürpriz: 6, 7, 8, 9
```

### 5.3. Ters sürpriz sayısı

Yalnızca favori `1 → 2` ve favori `2 → 1` dönüşleri sayılır.

Beraberlikler bu sayaca girmez.

Örnek:

```text
9 maçta ters sürpriz aranıyor
İzin verilen ters sürpriz: 2, 3, 4, 5, 6
```

### 5.4. `1` sayısı

15 maçın tamamındaki ev sahibi galibiyeti sayısıdır.

- Banko `1` maçları bu sayıya dahil edilir.
- Kullanıcının izin verdiği toplam aralık dışında kalan kolonlar elenir.

### 5.5. `2` sayısı

15 maçın tamamındaki deplasman galibiyeti sayısıdır.

- Banko `2` maçları bu sayıya dahil edilir.
- Kullanıcının izin verdiği toplam aralık dışında kalan kolonlar elenir.

### 5.6. Art arda `1` sayısı

Kolondaki değişken sonuçlar arasında arka arkaya gelen ev sahibi galibiyetlerinin maksimum serisini filtreler.

- Bankolar bu seriye dahil edilmez.
- Örneğin maksimum izin 4 ise 5 veya daha uzun seri taşıyan kolonlar elenir.

### 5.7. Art arda `X` sayısı

Kolondaki değişken sonuçlar arasında arka arkaya gelen beraberliklerin maksimum serisini filtreler.

- Bankolar seriyi bozmuş kabul edilir.
- Kullanıcı bu filtreyi kullanmak zorunda değildir.

### 5.8. Art arda `2` sayısı

Kolondaki değişken sonuçlar arasında arka arkaya gelen deplasman galibiyetlerinin maksimum serisini filtreler.

- Bankolar seriye dahil edilmez.
- Örneğin maksimum 3 seçilmişse 4 veya daha uzun seri elenir.

## 6. Maç grubu filtreleri

Filtreler tüm 15 maça uygulanmak zorunda değildir.

Desteklenen gruplar:

- 1–9 maçları
- 10–15 maçları
- Kullanıcının seçtiği özel maç grubu
- İlk veya son belirli maç grubu

Örnek özel grup:

```text
4, 6, 8, 12, 14 numaralı maçlar
Bu grupta izin verilen sürpriz sayısı: 2, 3, 4
```

Bu filtre yalnızca seçilen beş maça uygulanır; diğer maçlar değerlendirmeyi etkilemez.

## 7. Özel Sistem ile garantili sistem farkı

### Garantili sistem

- Ana kombinasyon oluşturulur.
- 12/13/14 garantili seçeneklerinden biri seçilir.
- Filtreler kullanılırsa yalnızca filtreye uyan garanti kolonları bırakılır.
- Tercihler doğru geldiğinde garanti seviyesi korunur.
- 15 sonucu şansa bağlıdır.

### Özel Sistem

- Ana kombinasyon oluşturulur.
- Seçilen tüm filtreleri sağlayan kolonlar bırakılır.
- Tercihler ve filtreler birlikte gerçekleşirse 15 sonucu kalan sistem içinde bulunur.
- Bu nedenle 15 olasılığı koşullu olarak yüzde 100 gösterilebilir.
- Filtrelerden biri gerçekleşmezse 15 seviyesi garanti değildir.

## 8. Uygulama için önerilen veri modeli

```python
@dataclass
class Hedef15FilterContext:
    favorite: str              # 1/X/2
    banko: str | None           # sabit sonuç, varsa
    variable: bool              # çifte/kapalı alanı mı?
    surprise_expected: bool

@dataclass
class Hedef15Filter:
    kind: str                  # draws, total_surprise, reverse_surprise, etc.
    match_indices: list[int]
    allowed_counts: set[int]
    max_streak: int | None = None

@dataclass
class FilterEvaluation:
    passed: bool
    observed_count: int
    allowed_counts: set[int]
    reason: str
```

## 9. Uygulama sırası

1. Banko/çifte/kapalı tercihleri doğrula.
2. Ana kartezyen kolonları oluştur.
3. Her kolon için sonuç sınıflarını hesapla:
   - toplam `1`
   - toplam `X`
   - toplam `2`
   - normal sürpriz
   - ters sürpriz
   - grup bazlı sayımlar
   - değişken sonuçlardaki art arda seriler
4. Kullanıcının seçtiği filtreleri sırayla uygula.
5. Her kolon için filtre geçiş raporu tut.
6. Kalan kolon sayısını ve elenen kolonların nedenlerini raporla.
7. Garanti modu seçiliyse garanti seviyesini hesapla.
8. Özel sistem seçiliyse filtrelerin tamamı gerçekleştiğinde kapsama durumunu doğrula.

## 10. Mutlaka korunacak kurallar

- `X` hiçbir durumda ters sürpriz olarak sayılmayacak.
- Bankolar art arda filtrelerine dahil edilmeyecek.
- Kullanılmayan filtre başarısızlık sebebi olmayacak.
- Filtreler tahmin üretmez; kolon eler.
- Filtre başarı koşulu açıkça raporlanacak.
- 15 garantisi koşulsuz ifade edilmeyecek.
- Ana kombinasyon ile filtre sonrası kolon kümesi ayrı tutulacak.
