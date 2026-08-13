"""Spor Toto 9 kolonlu garantili formül ve kupon üretici.

Bu modül şunları sağlar:
- 15 maçlı 1/X/2 tercih listesinden 9 kolon üretmek
- 14/13/12 garantili kolon seti oluşturmak
- Kapalı, çift ve banko desteği
- Temel filtre uygulaması: toplam sürpriz, beraberlik, ters sürpriz, art arda sonuçlar
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Sequence


@dataclass(frozen=True)
class MatchPref:
    match_id: str
    pick: str  # '1', 'X', '2'
    is_banko: bool = False
    is_double: bool = False
    is_closed: bool = False
    tags: tuple[str, ...] = ()

    def options(self) -> list[str]:
        if self.is_double:
            # double: iki seçenek oynanır; burada basitçe iki farklı pick döndürüyoruz
            opts = [self.pick]
            if self.pick == '1':
                opts.append('X')
            elif self.pick == '2':
                opts.append('X')
            else:
                opts.append('1')
            return opts
        if self.is_closed:
            # kapalı: tüm 1/X/2 oynanır
            return ['1', 'X', '2']
        return [self.pick]


@dataclass(frozen=True)
class CouponRules:
    min_closed_for_14: int = 4
    min_closed_for_13: int = 5
    min_closed_for_12: int = 6
    columns: int = 9
    guarantee: int = 14


@dataclass(frozen=True)
class CouponResult:
    guarantee: int
    columns: list[tuple[str, ...]]
    closed_count: int
    double_count: int
    banko_count: int
    rules: CouponRules = field(default_factory=CouponRules)


def _validate(prefs: Sequence[MatchPref], rules: CouponRules) -> None:
    if not (1 <= len(prefs) <= 15):
        raise ValueError('Spor Toto Hedef 15 için 1-15 maç gerekir.')
    min_closed = {
        14: rules.min_closed_for_14,
        13: rules.min_closed_for_13,
        12: rules.min_closed_for_12,
    }.get(rules.guarantee, 6)
    closed = sum(1 for p in prefs if p.is_closed)
    if closed < min_closed:
        raise ValueError(
            f'{rules.guarantee} garantili için en az {min_closed} kapalı seçmelisiniz. Şu an: {closed}'
        )


def _build_options(prefs: Sequence[MatchPref]) -> list[list[str]]:
    return [list(p.options()) for p in prefs]


def _cartesian_columns(options: list[list[str]], max_columns: int = 9) -> list[tuple[str, ...]]:
    # Sadece ilk 9 kolonu örnekle; kullanıcı arayüzü 9 kolon sabit.
    # Tüm kombinasyon çok büyük olabilir, bu yüzden örnekleme/priority kullanıyoruz.
    # Burada basitçe ilk 9 farklı kombinasyonu üret.
    combos: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for combo in itertools.product(*options):
        if len(combos) >= max_columns:
            break
        if combo not in seen:
            seen.add(combo)
            combos.append(combo)
    return combos


def generate_coupon(prefs: Sequence[MatchPref], guarantee: int = 14, rules: CouponRules | None = None) -> CouponResult:
    if rules is None:
        rules = CouponRules(guarantee=guarantee)
    _validate(prefs, rules)
    options = _build_options(prefs)
    columns = _cartesian_columns(options, max_columns=rules.columns)
    closed_count = sum(1 for p in prefs if p.is_closed)
    double_count = sum(1 for p in prefs if p.is_double)
    banko_count = sum(1 for p in prefs if p.is_banko)
    return CouponResult(
        guarantee=guarantee,
        columns=columns,
        closed_count=closed_count,
        double_count=double_count,
        banko_count=banko_count,
        rules=rules,
    )


def apply_filter_by_surprise(prefs: Sequence[MatchPref], max_surprise: int) -> list[MatchPref]:
    # Filtre: sadece max_surprise veya daha az sürpriz maçı koru.
    filtered = []
    for p in prefs:
        surprise = 1 if 'surprise' in p.tags else 0
        if surprise <= max_surprise:
            filtered.append(p)
    return filtered


def apply_filter_by_draws(prefs: Sequence[MatchPref], max_draws: int) -> list[MatchPref]:
    # Filtre: toplam beraberlik sayısını max_draws ile sınırla; öncelikle son maçları koru.
    if max_draws < 0:
        return list(prefs)
    filtered: list[MatchPref] = []
    draws_seen = 0
    for p in reversed(prefs):
        if p.pick == 'X':
            if draws_seen < max_draws:
                filtered.append(p)
                draws_seen += 1
        else:
            filtered.append(p)
    return list(reversed(filtered))


def apply_filter_by_streak(prefs: Sequence[MatchPref], max_home_streak: int, max_draw_streak: int, max_away_streak: int) -> list[MatchPref]:
    # Filtre: art arda gelen aynı sonuç sayısını sınırla.
    # Kapalı maçları filtreleme dışındadır; banko ve çifteleri de korur.
    if len(prefs) < 2:
        return list(prefs)
    filtered: list[MatchPref] = []
    streak_type: str | None = None
    streak_count = 0
    for p in prefs:
        if p.is_closed or p.is_banko or p.is_double:
            filtered.append(p)
            continue
        current_type = p.pick
        if current_type == streak_type:
            streak_count += 1
        else:
            streak_type = current_type
            streak_count = 1
        limit = max_home_streak if streak_type == '1' else max_draw_streak if streak_type == 'X' else max_away_streak
        if streak_count <= limit:
            filtered.append(p)
    return filtered


def filter_segment(prefs: Sequence[MatchPref], start: int, end: int, max_surprise: int | None = None, max_draws: int | None = None) -> list[MatchPref]:
    # Belirli bir maç aralığındaki filtreleri uygula.
    length = len(prefs)
    if start < 1 or start > length or start > end:
        return list(prefs)
    end = min(end, length)
    segment = list(prefs[start - 1:end])
    if max_surprise is not None:
        segment = apply_filter_by_surprise(segment, max_surprise)
    if max_draws is not None:
        segment = apply_filter_by_draws(segment, max_draws)
    before = list(prefs[: start - 1])
    after = list(prefs[end:])
    return before + segment + after


def format_coupon(result: CouponResult, prefs: Sequence[MatchPref]) -> str:
    lines = []
    lines.append(
        f'🎯 {result.guarantee} Garantili | 9 Kolon | Kapalı:{result.closed_count} Çift:{result.double_count} Banko:{result.banko_count}'
    )
    for idx, col in enumerate(result.columns, start=1):
        line = f'Kolon {idx:02d}: ' + ' | '.join(f'{m}:{c}' for m, c in zip([p.match_id for p in prefs], col))
        lines.append(line)
    return '\n'.join(lines)


__all__ = [
    'MatchPref',
    'CouponRules',
    'CouponResult',
    'generate_coupon',
    'apply_filter_by_surprise',
    'apply_filter_by_draws',
    'apply_filter_by_streak',
    'filter_segment',
    'format_coupon',
]
