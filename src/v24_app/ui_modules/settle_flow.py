from __future__ import annotations

from typing import Any, Callable, Mapping


def parse_settlement_score_inputs(home_text: str, away_text: str) -> tuple[int, int]:
    return int(str(home_text).strip()), int(str(away_text).strip())


def is_settlement_score_in_range(home_goals: int, away_goals: int, *, min_goals: int = 0, max_goals: int = 20) -> bool:
    return min_goals <= int(home_goals) <= max_goals and min_goals <= int(away_goals) <= max_goals


def build_settlement_status_text(
    *,
    match: Any,
    home_goals: int,
    away_goals: int,
    settlement: Mapping[str, object],
    mark_text_fn: Callable[[object], str],
) -> str:
    total_mark = mark_text_fn(settlement.get("total_goals_is_correct"))
    score_mark = mark_text_fn(settlement.get("score_is_correct"))
    return (
        f"已结算 {getattr(match, 'home_team', '-')} {int(home_goals)}-{int(away_goals)} {getattr(match, 'away_team', '-')} | "
        f"赛果:{settlement.get('result', '-')} | 让球:{settlement.get('predicted_handicap') or '-'} 命中:{mark_text_fn(settlement.get('handicap_is_correct'))} | "
        f"总进球:{settlement.get('predicted_total_goals') or '-'}->{settlement.get('total_goals', '-')} 命中:{total_mark} | "
        f"比分命中:{score_mark}"
    )
