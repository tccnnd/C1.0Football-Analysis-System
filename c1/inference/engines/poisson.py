from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import exp, factorial


@dataclass
class PoissonOutcome:
    home_lambda: float
    away_lambda: float
    home_win: float
    draw: float
    away_win: float
    over_2_5: float
    under_2_5: float
    btts_yes: float
    btts_no: float
    score_distribution: list[dict]
    top_scores: list[dict]
    total_goals_distribution: list[dict]
    top_total_goals: list[dict]
    best_total_goals: int
    best_total_goals_prob: float
    halftime_probabilities: dict[str, float]
    htft_probabilities: dict[str, float]
    htft_top: list[dict]
    best_htft: str
    best_htft_prob: float


class PoissonScoreEngine:
    """Poisson score-distribution engine for stage-3 forecasting."""

    def __init__(self, max_goals: int = 6) -> None:
        self.max_goals = max_goals

    def _pmf(self, goals: int, rate: float) -> float:
        return (rate**goals) * exp(-rate) / factorial(goals)

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(value, high))

    def _result_key(self, home_goals: int, away_goals: int) -> str:
        if home_goals > away_goals:
            return "home"
        if home_goals < away_goals:
            return "away"
        return "draw"

    def _htft_label(self, key: str) -> str:
        mapping = {"home": "胜", "draw": "平", "away": "负"}
        left, right = key.split("_", 1)
        return f"{mapping.get(left, '-')} / {mapping.get(right, '-')}"

    def estimate_lambdas(
        self,
        home_rating: float,
        away_rating: float,
        market_draw_prob: float,
        league_strength: float,
    ) -> tuple[float, float]:
        rating_diff = home_rating - away_rating

        # Lower draw probability usually indicates a higher expected total-goals environment.
        total_goals = 2.65 + (0.24 - market_draw_prob) * 2.0 + (league_strength - 0.92) * 0.35
        total_goals = self._clamp(total_goals, 1.8, 3.9)

        home_share = 0.50 + rating_diff / 900.0
        home_share = self._clamp(home_share, 0.34, 0.68)

        home_lambda = total_goals * home_share
        away_lambda = total_goals - home_lambda

        return max(home_lambda, 0.2), max(away_lambda, 0.2)

    def predict(
        self,
        home_rating: float,
        away_rating: float,
        market_draw_prob: float,
        league_strength: float,
    ) -> PoissonOutcome:
        home_lambda, away_lambda = self.estimate_lambdas(
            home_rating=home_rating,
            away_rating=away_rating,
            market_draw_prob=market_draw_prob,
            league_strength=league_strength,
        )

        home_probs = [self._pmf(i, home_lambda) for i in range(self.max_goals + 1)]
        away_probs = [self._pmf(i, away_lambda) for i in range(self.max_goals + 1)]

        score_grid: list[dict] = []
        total_goals_map: dict[int, float] = defaultdict(float)
        home_win = 0.0
        draw = 0.0
        away_win = 0.0
        over_2_5 = 0.0
        btts_yes = 0.0

        for home_goals in range(self.max_goals + 1):
            for away_goals in range(self.max_goals + 1):
                p = home_probs[home_goals] * away_probs[away_goals]
                score_grid.append({"score": f"{home_goals}-{away_goals}", "probability": p})

                if home_goals > away_goals:
                    home_win += p
                elif home_goals == away_goals:
                    draw += p
                else:
                    away_win += p

                total_goals_map[home_goals + away_goals] += p

                if home_goals + away_goals >= 3:
                    over_2_5 += p

                if home_goals > 0 and away_goals > 0:
                    btts_yes += p

        mass_total = home_win + draw + away_win
        if mass_total <= 0:
            mass_total = 1.0

        home_win /= mass_total
        draw /= mass_total
        away_win /= mass_total
        over_2_5 /= mass_total
        btts_yes /= mass_total

        score_distribution = [
            {
                "score": item["score"],
                "probability": round(item["probability"] / mass_total, 4),
            }
            for item in sorted(score_grid, key=lambda entry: entry["probability"], reverse=True)
        ]
        top_scores = score_distribution[:5]
        total_goals_distribution = [
            {
                "goals": goals,
                "probability": round(total_goals_map[goals] / mass_total, 4),
            }
            for goals in sorted(total_goals_map)
        ]
        top_total_goals = sorted(
            total_goals_distribution,
            key=lambda item: (-item["probability"], item["goals"]),
        )[:5]
        best_total_goals = int(top_total_goals[0]["goals"]) if top_total_goals else 0
        best_total_goals_prob = float(top_total_goals[0]["probability"]) if top_total_goals else 0.0

        halftime_share = 0.46
        home_ht_lambda = max(home_lambda * halftime_share, 0.05)
        away_ht_lambda = max(away_lambda * halftime_share, 0.05)
        home_sh_lambda = max(home_lambda - home_ht_lambda, 0.05)
        away_sh_lambda = max(away_lambda - away_ht_lambda, 0.05)

        home_ht_probs = [self._pmf(i, home_ht_lambda) for i in range(self.max_goals + 1)]
        away_ht_probs = [self._pmf(i, away_ht_lambda) for i in range(self.max_goals + 1)]
        home_sh_probs = [self._pmf(i, home_sh_lambda) for i in range(self.max_goals + 1)]
        away_sh_probs = [self._pmf(i, away_sh_lambda) for i in range(self.max_goals + 1)]

        halftime_result_probs = {"home": 0.0, "draw": 0.0, "away": 0.0}
        htft_map = {
            f"{ht_key}_{ft_key}": 0.0
            for ht_key in ("home", "draw", "away")
            for ft_key in ("home", "draw", "away")
        }

        for ht_home_goals in range(self.max_goals + 1):
            for ht_away_goals in range(self.max_goals + 1):
                halftime_prob = home_ht_probs[ht_home_goals] * away_ht_probs[ht_away_goals]
                ht_key = self._result_key(ht_home_goals, ht_away_goals)
                halftime_result_probs[ht_key] += halftime_prob

                for sh_home_goals in range(self.max_goals + 1):
                    for sh_away_goals in range(self.max_goals + 1):
                        probability = halftime_prob * home_sh_probs[sh_home_goals] * away_sh_probs[sh_away_goals]
                        ft_key = self._result_key(
                            ht_home_goals + sh_home_goals,
                            ht_away_goals + sh_away_goals,
                        )
                        htft_map[f"{ht_key}_{ft_key}"] += probability

        halftime_mass = sum(halftime_result_probs.values()) or 1.0
        htft_mass = sum(htft_map.values()) or 1.0
        halftime_probabilities = {
            key: round(value / halftime_mass, 4) for key, value in halftime_result_probs.items()
        }
        htft_probabilities = {
            key: round(value / htft_mass, 4) for key, value in htft_map.items()
        }
        htft_top = sorted(
            (
                {
                    "key": key,
                    "label": self._htft_label(key),
                    "probability": probability,
                }
                for key, probability in htft_probabilities.items()
            ),
            key=lambda item: (-item["probability"], item["label"]),
        )[:5]
        best_htft = str(htft_top[0]["label"]) if htft_top else "-"
        best_htft_prob = float(htft_top[0]["probability"]) if htft_top else 0.0

        return PoissonOutcome(
            home_lambda=home_lambda,
            away_lambda=away_lambda,
            home_win=home_win,
            draw=draw,
            away_win=away_win,
            over_2_5=over_2_5,
            under_2_5=max(0.0, 1.0 - over_2_5),
            btts_yes=btts_yes,
            btts_no=max(0.0, 1.0 - btts_yes),
            score_distribution=score_distribution,
            top_scores=top_scores,
            total_goals_distribution=total_goals_distribution,
            top_total_goals=top_total_goals,
            best_total_goals=best_total_goals,
            best_total_goals_prob=best_total_goals_prob,
            halftime_probabilities=halftime_probabilities,
            htft_probabilities=htft_probabilities,
            htft_top=htft_top,
            best_htft=best_htft,
            best_htft_prob=best_htft_prob,
        )
