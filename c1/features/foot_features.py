"""
foot (Go) 信号特征提取

将 foot MySQL 桥接层的信号转换为 C1.0 Feature Layer 可用的字段。

集成原则：
- foot 信号作为补充特征，不替换现有 C1.0 字段
- 所有 foot 字段以 foot_ 前缀隔离，避免命名冲突
- 桥接失败时静默降级，不影响主流程
- foot 信号可增强 chaos_score 和 market_divergence 的计算
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# foot 信号对 chaos_score 的贡献权重
_FOOT_CHAOS_WEIGHT = 0.12
# foot 欧亚冲突对 market_divergence 的贡献权重
_FOOT_DIVERGENCE_WEIGHT = 0.15


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except Exception:
        return default


def _clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


# ── 核心：从 foot 桥接层获取信号 ─────────────────────────────────────────────

def fetch_foot_signals(
    main_team_id: str,
    guest_team_id: str,
    match_date: str,
    match_id: str | None = None,
) -> dict[str, Any]:
    """
    从 foot MySQL 获取信号，返回 as_feature_dict 格式。
    失败时返回空字典（静默降级）。
    """
    try:
        from c1.data.foot_bridge import get_foot_bridge
        bridge = get_foot_bridge()
        if not bridge.enabled:
            return {}
        signals = bridge.get_signals_for_match(
            main_team_id=main_team_id,
            guest_team_id=guest_team_id,
            match_date=match_date,
            match_id=match_id,
        )
        if not signals.has_data:
            return {}
        return signals.as_feature_dict
    except Exception as exc:
        logger.debug("foot_features: 获取信号失败 %s vs %s: %s", main_team_id, guest_team_id, exc)
        return {}


# ── 信号解读：将 foot 原始信号转为语义特征 ───────────────────────────────────

def compute_foot_asia_signal_strength(foot_fields: dict[str, Any]) -> float:
    """
    亚赔信号强度 [0, 1]。
    综合方向共识度和让球变化幅度。
    """
    direction = int(foot_fields.get("foot_asia_direction", -1))
    if direction == -1:
        return 0.0
    consensus = _safe_float(foot_fields.get("foot_asia_direction_consensus"), 0.0)
    let_ball_move = abs(_safe_float(foot_fields.get("foot_asia_let_ball_move"), 0.0))
    # 让球变化 0.25 以上视为显著
    move_signal = _clip(let_ball_move / 0.25)
    return round(_clip(consensus * 0.6 + move_signal * 0.4), 4)


def compute_foot_euro_asia_conflict_score(foot_fields: dict[str, Any]) -> float:
    """
    欧亚联动冲突分数 [0, 1]。
    A1 模型核心信号：欧赔和亚赔方向相反时为 1.0。
    """
    conflict = int(foot_fields.get("foot_euro_asia_conflict", 0))
    if not conflict:
        return 0.0
    # 有冲突时，用亚赔共识度加权
    consensus = _safe_float(foot_fields.get("foot_asia_direction_consensus"), 0.5)
    return round(_clip(consensus), 4)


def compute_foot_fundamental_score(foot_fields: dict[str, Any]) -> float:
    """
    基本面综合分数 [0, 1]，对应 C1 模型逻辑。
    综合积分榜差距、对战历史、近期战绩。
    """
    ranking_diff = _safe_float(foot_fields.get("foot_ranking_diff"), 0.0)
    h2h = _safe_float(foot_fields.get("foot_h2h_main_win_rate"), 0.0)
    recent_main = _safe_float(foot_fields.get("foot_recent_main_win_rate"), 0.0)
    recent_guest = _safe_float(foot_fields.get("foot_recent_guest_win_rate"), 0.0)

    # 排名差归一化（差距越大信号越强，负值=主队排名更好）
    ranking_signal = _clip(abs(ranking_diff) / 10.0)

    # 近期战绩差异
    recent_diff = abs(recent_main - recent_guest)

    score = ranking_signal * 0.4 + h2h * 0.3 + recent_diff * 0.3
    return round(_clip(score), 4)


def compute_foot_model_agreement(
    foot_fields: dict[str, Any],
    predicted_side: str,
) -> float:
    """
    foot 模型与 C1.0 预测方向的一致性 [0, 1]。
    - 1.0：foot 多模型共识与 C1.0 预测方向一致
    - 0.5：foot 无共识
    - 0.0：foot 多模型共识与 C1.0 预测方向相反
    """
    consensus = int(foot_fields.get("foot_model_consensus", -1))
    count = int(foot_fields.get("foot_model_consensus_count", 0))
    conflict = int(foot_fields.get("foot_model_conflict", 0))

    if consensus == -1 or count == 0:
        return 0.5  # 无数据，中性

    # foot 模型结论：3=主胜 1=平 0=客胜
    # C1.0 predicted_side：home/draw/away
    side_map = {3: "home", 1: "draw", 0: "away"}
    foot_side = side_map.get(consensus, "")

    if not foot_side or not predicted_side:
        return 0.5

    if foot_side == predicted_side:
        # 一致，模型数量越多越强
        strength = _clip(count / 3.0)
        return round(0.5 + 0.5 * strength, 4)
    else:
        # 冲突
        return round(0.0 if conflict else 0.25, 4)


# ── 主入口：增强 raw_fields ───────────────────────────────────────────────────

def enrich_with_foot_signals(
    raw_fields: dict[str, Any],
    *,
    predicted_side: str = "",
) -> dict[str, Any]:
    """
    用 foot 信号增强 raw_fields。

    从 raw_fields 中提取队名和日期，查询 foot MySQL，
    将信号注入 raw_fields 并更新相关复合特征。

    raw_fields 需要包含：
    - home_team / main_team_id
    - away_team / guest_team_id
    - match_date
    - (可选) match_id / source_id

    返回增强后的 raw_fields 副本。
    """
    fields = dict(raw_fields)

    # 提取队名和日期
    main_team = str(
        fields.get("home_team") or fields.get("main_team_id") or ""
    ).strip()
    guest_team = str(
        fields.get("away_team") or fields.get("guest_team_id") or ""
    ).strip()
    match_date = str(fields.get("match_date", "")).strip()
    match_id = str(fields.get("match_id") or fields.get("source_id") or "").strip() or None

    if not main_team or not guest_team or not match_date:
        fields["foot_signals_available"] = False
        return fields

    # 获取 foot 信号
    foot_fields = fetch_foot_signals(
        main_team_id=main_team,
        guest_team_id=guest_team,
        match_date=match_date,
        match_id=match_id,
    )

    if not foot_fields:
        fields["foot_signals_available"] = False
        return fields

    # 注入原始 foot 信号
    fields.update(foot_fields)
    fields["foot_signals_available"] = True

    # ── 计算语义特征 ──
    asia_strength = compute_foot_asia_signal_strength(foot_fields)
    euro_asia_conflict = compute_foot_euro_asia_conflict_score(foot_fields)
    fundamental_score = compute_foot_fundamental_score(foot_fields)
    model_agreement = compute_foot_model_agreement(foot_fields, predicted_side)

    fields["foot_asia_signal_strength"] = asia_strength
    fields["foot_euro_asia_conflict_score"] = euro_asia_conflict
    fields["foot_fundamental_score"] = fundamental_score
    fields["foot_model_agreement"] = model_agreement

    # ── 增强 market_divergence ──
    # 欧亚联动冲突是市场分歧的强信号
    existing_divergence = _safe_float(fields.get("market_divergence"), 0.0)
    foot_divergence_contribution = euro_asia_conflict * _FOOT_DIVERGENCE_WEIGHT
    fields["market_divergence"] = round(
        _clip(existing_divergence + foot_divergence_contribution), 4
    )

    # ── 增强 chaos_score（如果已计算）──
    # foot 亚赔信号强度和欧亚冲突都是混乱度的来源
    if "chaos_score" in fields:
        foot_chaos = (asia_strength * 0.5 + euro_asia_conflict * 0.5) * _FOOT_CHAOS_WEIGHT
        fields["chaos_score"] = round(
            _clip(_safe_float(fields["chaos_score"]) + foot_chaos), 4
        )

    return fields
