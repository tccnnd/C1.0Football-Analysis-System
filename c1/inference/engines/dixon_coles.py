"""
Dixon-Coles 修正引擎

Dixon-Coles (1997) 的核心贡献是修正独立 Poisson 模型在低比分场景的偏差。
具体来说，0-0, 1-0, 0-1, 1-1 四种比分的概率需要用 ρ 因子调整。

本实现不做完整的 MLE 参数估计（太慢），
而是直接在 Poisson 模型输出上应用 ρ 修正。
ρ 的经验值约为 -0.13（来自文献和实证）。

这样既获得了 Dixon-Coles 的核心收益，又保持了毫秒级推理速度。
"""
from __future__ import annotations

import logging
from math import exp
from typing import Any

logger = logging.getLogger(__name__)

# Dixon-Coles ρ 参数（经验值，负值表示低比分出现频率高于独立 Poisson 预测）
DEFAULT_RHO = -0.13


def dixon_coles_correction(
    home_lambda: float,
    away_lambda: float,
    rho: float = DEFAULT_RHO,
    max_goals: int = 8,
) -> dict[str, float]:
    """
    对 Poisson 比分矩阵应用 Dixon-Coles ρ 修正，返回 1X2 概率。

    Args:
        home_lambda: 主队预期进球（Poisson λ）
        away_lambda: 客队预期进球
        rho: Dixon-Coles 修正因子（默认 -0.13）
        max_goals: 最大进球数

    Returns:
        {"home": float, "draw": float, "away": float}
    """
    from math import factorial

    def poisson_pmf(k: int, lam: float) -> float:
        if lam <= 0:
            return 1.0 if k == 0 else 0.0
        return (lam ** k) * exp(-lam) / factorial(k)

    def tau(x: int, y: int, lam: float, mu: float, rho_val: float) -> float:
        """Dixon-Coles 修正因子 τ"""
        if x == 0 and y == 0:
            return 1.0 - lam * mu * rho_val
        elif x == 0 and y == 1:
            return 1.0 + lam * rho_val
        elif x == 1 and y == 0:
            return 1.0 + mu * rho_val
        elif x == 1 and y == 1:
            return 1.0 - rho_val
        return 1.0

    home_win = 0.0
    draw = 0.0
    away_win = 0.0

    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p_ij = poisson_pmf(i, home_lambda) * poisson_pmf(j, away_lambda)
            # 对低比分应用 ρ 修正
            p_ij *= tau(i, j, home_lambda, away_lambda, rho)
            p_ij = max(p_ij, 0.0)  # 确保非负

            if i > j:
                home_win += p_ij
            elif i == j:
                draw += p_ij
            else:
                away_win += p_ij

    total = max(home_win + draw + away_win, 1e-9)
    return {
        "home": round(home_win / total, 6),
        "draw": round(draw / total, 6),
        "away": round(away_win / total, 6),
    }


def dixon_coles_expected_goals(
    home_rating: float,
    away_rating: float,
    league_avg_goals: float = 2.7,
    home_advantage: float = 0.3,
) -> tuple[float, float]:
    """
    从 ELO 评分估算 Poisson λ 参数。

    Returns:
        (home_lambda, away_lambda)
    """
    # 评分差转换为进球期望
    rating_diff = (home_rating - away_rating) / 400.0
    home_strength = 10 ** (rating_diff / 2.0)
    away_strength = 1.0 / home_strength

    # 归一化到联赛平均进球
    total_strength = home_strength + away_strength
    home_lambda = (home_strength / total_strength) * league_avg_goals * (1.0 + home_advantage / league_avg_goals)
    away_lambda = (away_strength / total_strength) * league_avg_goals * (1.0 - home_advantage / league_avg_goals * 0.5)

    return max(0.1, home_lambda), max(0.1, away_lambda)


class DixonColesEngine:
    """
    轻量级 Dixon-Coles 引擎。

    不做 MLE 参数估计，直接在 Poisson λ 上应用 ρ 修正。
    """

    def __init__(self, rho: float = DEFAULT_RHO) -> None:
        self.rho = rho

    @property
    def available(self) -> bool:
        return True

    @property
    def fitted(self) -> bool:
        return True  # 不需要拟合

    def predict(
        self,
        home_lambda: float,
        away_lambda: float,
    ) -> dict[str, float]:
        """从 Poisson λ 预测 1X2 概率（含 ρ 修正）"""
        return dixon_coles_correction(home_lambda, away_lambda, self.rho)

    def predict_from_ratings(
        self,
        home_rating: float,
        away_rating: float,
        league_avg_goals: float = 2.7,
    ) -> dict[str, float]:
        """从 ELO 评分预测 1X2 概率"""
        home_lambda, away_lambda = dixon_coles_expected_goals(
            home_rating, away_rating, league_avg_goals
        )
        return self.predict(home_lambda, away_lambda)
