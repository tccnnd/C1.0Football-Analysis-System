from __future__ import annotations

from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def compute_return_rate(
    odds_home: Any,
    odds_draw: Any,
    odds_away: Any,
    raw_return_rate: Any = 0.0,
) -> float:
    direct = safe_float(raw_return_rate, default=0.0)
    if direct > 0.0:
        return direct
    implied_total = (
        1.0 / max(safe_float(odds_home, default=0.0), 1.01)
        + 1.0 / max(safe_float(odds_draw, default=0.0), 1.01)
        + 1.0 / max(safe_float(odds_away, default=0.0), 1.01)
    )
    return 1.0 / max(implied_total, 1e-9)


def build_market_intent_feature_map(
    *,
    odds_home: Any,
    odds_draw: Any,
    odds_away: Any,
    opening_odds_home: Any = 0.0,
    opening_odds_draw: Any = 0.0,
    opening_odds_away: Any = 0.0,
    return_rate: Any = 0.0,
    kelly_home: Any = 0.0,
    kelly_draw: Any = 0.0,
    kelly_away: Any = 0.0,
) -> dict[str, float]:
    current_home = max(safe_float(odds_home, default=0.0), 1.01)
    current_draw = max(safe_float(odds_draw, default=0.0), 1.01)
    current_away = max(safe_float(odds_away, default=0.0), 1.01)
    open_home = safe_float(opening_odds_home, default=0.0)
    open_draw = safe_float(opening_odds_draw, default=0.0)
    open_away = safe_float(opening_odds_away, default=0.0)
    rate = compute_return_rate(current_home, current_draw, current_away, raw_return_rate=return_rate)
    implied_home = 1.0 / current_home
    implied_draw = 1.0 / current_draw
    implied_away = 1.0 / current_away
    implied_total = max(implied_home + implied_draw + implied_away, 1e-9)
    market_home = implied_home / implied_total
    market_draw = implied_draw / implied_total
    market_away = implied_away / implied_total
    kh = safe_float(kelly_home, default=0.0)
    kd = safe_float(kelly_draw, default=0.0)
    ka = safe_float(kelly_away, default=0.0)
    kelly_draw_edge = 0.0
    if min(kh, kd, ka) > 0.0:
        kelly_draw_edge = ((kh + ka) / 2.0) - kd

    return {
        "opening_odds_home": round(open_home, 4),
        "opening_odds_draw": round(open_draw, 4),
        "opening_odds_away": round(open_away, 4),
        "return_rate": round(rate, 4),
        "market_overround": round(max(0.0, 1.0 - rate), 4),
        "home_odds_drop": round((open_home - current_home) if open_home > 1.0 else 0.0, 4),
        "draw_odds_drop": round((open_draw - current_draw) if open_draw > 1.0 else 0.0, 4),
        "away_odds_drop": round((open_away - current_away) if open_away > 1.0 else 0.0, 4),
        "kelly_home": round(kh, 4),
        "kelly_draw": round(kd, 4),
        "kelly_away": round(ka, 4),
        "kelly_draw_edge": round(kelly_draw_edge, 4),
        "market_balance": round(1.0 - abs(market_home - market_away), 4),
    }
