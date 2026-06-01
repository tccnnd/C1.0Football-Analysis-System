from __future__ import annotations

from dataclasses import dataclass
from math import log10


@dataclass
class EloSnapshot:
    home_rating: float
    away_rating: float
    rating_diff: float
    home_win: float
    draw: float
    away_win: float


@dataclass
class EloUpdate:
    home_before: float
    away_before: float
    home_after: float
    away_after: float
    delta_home: float
    delta_away: float
    expected_home: float
    expected_away: float


class EloRatingEngine:
    """Elo engine with both pre-match inference and post-match updates."""

    def __init__(self, base_rating: float = 1500.0, home_advantage: float = 65.0, k_factor: float = 24.0) -> None:
        self.base_rating = base_rating
        self.home_advantage = home_advantage
        self.k_factor = k_factor

    def _expected_score(self, rating_diff: float) -> float:
        return 1.0 / (1.0 + 10 ** (-rating_diff / 400.0))

    def _draw_prob(self, implied_draw: float, rating_diff: float) -> float:
        gap_penalty = min(abs(rating_diff) / 2000.0, 0.10)
        draw = 0.24 + (implied_draw - 0.24) * 0.55 - gap_penalty
        return max(0.14, min(draw, 0.33))

    def from_market(
        self,
        home_prob: float,
        draw_prob: float,
        away_prob: float,
        league_strength: float,
    ) -> EloSnapshot:
        expected_home_score = home_prob + draw_prob * 0.5
        expected_home_score = max(0.06, min(expected_home_score, 0.94))
        market_diff = 400.0 * log10(expected_home_score / (1.0 - expected_home_score))

        scaled_diff = market_diff * (0.78 + 0.22 * league_strength)
        rating_diff = scaled_diff + self.home_advantage
        home_rating = self.base_rating + rating_diff / 2.0
        away_rating = self.base_rating - rating_diff / 2.0

        return self.from_ratings(home_rating, away_rating, draw_prob)

    def from_ratings(self, home_rating: float, away_rating: float, implied_draw: float = 0.24) -> EloSnapshot:
        rating_diff = (home_rating + self.home_advantage) - away_rating
        elo_home_score = self._expected_score(rating_diff)
        elo_draw = self._draw_prob(implied_draw, rating_diff)
        elo_home = max(0.03, elo_home_score - elo_draw * 0.5)
        elo_away = max(0.03, 1.0 - elo_home - elo_draw)

        total = elo_home + elo_draw + elo_away
        elo_home /= total
        elo_draw /= total
        elo_away /= total

        return EloSnapshot(
            home_rating=home_rating,
            away_rating=away_rating,
            rating_diff=home_rating - away_rating,
            home_win=elo_home,
            draw=elo_draw,
            away_win=elo_away,
        )

    def update_from_result(
        self,
        home_rating: float,
        away_rating: float,
        home_goals: int,
        away_goals: int,
        league_strength: float = 1.0,
    ) -> EloUpdate:
        expected_home = self._expected_score((home_rating + self.home_advantage) - away_rating)
        expected_away = 1.0 - expected_home

        if home_goals > away_goals:
            actual_home = 1.0
            actual_away = 0.0
        elif home_goals < away_goals:
            actual_home = 0.0
            actual_away = 1.0
        else:
            actual_home = 0.5
            actual_away = 0.5

        goal_diff = abs(home_goals - away_goals)
        margin_multiplier = 1.0 + min(goal_diff, 4) * 0.12
        dynamic_k = self.k_factor * (0.85 + 0.30 * league_strength) * margin_multiplier

        delta_home = dynamic_k * (actual_home - expected_home)
        delta_away = dynamic_k * (actual_away - expected_away)

        home_after = home_rating + delta_home
        away_after = away_rating + delta_away

        return EloUpdate(
            home_before=home_rating,
            away_before=away_rating,
            home_after=home_after,
            away_after=away_after,
            delta_home=delta_home,
            delta_away=delta_away,
            expected_home=expected_home,
            expected_away=expected_away,
        )
