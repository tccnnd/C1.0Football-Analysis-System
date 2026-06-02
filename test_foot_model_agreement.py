"""
foot_model_agreement 接入 Governance 决策逻辑测试

覆盖场景：
1. 高一致性 → foot_model_confirmed tag，不影响 APPROVE
2. 低一致性 + 软冲突 → observe 阈值降低，更容易触发 OBSERVE
3. 极低一致性 + 软冲突 → 强制 OBSERVE
4. 无 foot 信号 → 向后兼容，行为不变
5. 真实历史数据端到端
"""
import sys
sys.path.insert(0, "src")

from c1.core.schema import FeatureSnapshot, PredictionSnapshot, GovernanceRequest
from c1.core.reason_codes import ReasonCode, DecisionAction
from c1.modules.judge import GovernanceJudge, load_governance_config

cfg = load_governance_config()
judge = GovernanceJudge(config=cfg)

def make_request(fields: dict, predicted_side: str = "home", confidence: float = 0.65):
    snap = FeatureSnapshot(match_id="test", feature_version="test", fields=fields)
    pred = PredictionSnapshot(
        model_name="xgboost_v0",
        raw_probabilities={"home": 0.55, "draw": 0.25, "away": 0.20},
        predicted_side=predicted_side,
        confidence=confidence,
    )
    return GovernanceRequest(match_id="test", feature_snapshot=snap, prediction_snapshot=pred)

def section(t): print(f"\n{'='*60}\n  {t}\n{'='*60}")
def check(label, cond):
    icon = "✅" if cond else "❌"
    print(f"  {icon} {label}")
    return cond

all_pass = True

# 基础字段（无冲突）
BASE = {
    "info_quality": 0.80, "lineup_known": True, "lineup_freshness_hours": 2.0,
    "missing_elo_loss": 0.0, "odds_move_against_model": 0.0,
    "line_move_against_model": 0.0, "chaos_score": 0.05,
    "market_divergence": 0.0, "injury_conflict_score": 0.0,
    "environment_safe": True, "predicted_side": "home", "market_side": "home",
}

# ── 场景 1：高一致性 → APPROVE + foot_model_confirmed ─────────────────────────
section("场景 1: 高一致性 (agreement=0.85) → APPROVE + foot_model_confirmed")
f1 = {**BASE,
    "foot_signals_available": True,
    "foot_model_agreement": 0.85,   # >= confirm=0.75
    "foot_model_consensus": 3, "foot_model_consensus_count": 2,
    "foot_model_conflict": 0, "foot_asia_direction": 3,
    "foot_asia_signal_strength": 0.3, "foot_euro_asia_conflict": False,
    "foot_euro_asia_conflict_score": 0.0,
}
d1 = judge.evaluate(make_request(f1))
print(f"  action: {d1.action}  tags: {d1.tags}")
print(f"  trace.foot_confirmed: {d1.trace.get('foot_confirmed')}")
all_pass &= check("action=APPROVE", d1.action == DecisionAction.APPROVE)
all_pass &= check("tag=foot_model_confirmed", "foot_model_confirmed" in d1.tags)
all_pass &= check("trace.foot_confirmed=True", d1.trace.get("foot_confirmed") is True)

# ── 场景 2：低一致性 + 2 个软冲突 → observe 阈值降为 2 → OBSERVE ──────────────
section("场景 2: 低一致性 (agreement=0.20) + 2 软冲突 → OBSERVE（阈值降为 2）")
f2 = {**BASE,
    "lineup_known": False,          # 软冲突 1: LINEUP_UNKNOWN
    "market_side": "away",          # 软冲突 2: MARKET_DIVERGENCE_SOFT
    "market_divergence": 0.15,
    "foot_signals_available": True,
    "foot_model_agreement": 0.20,   # < weak=0.30 → 阈值降为 2
    "foot_model_consensus": 0, "foot_model_consensus_count": 2,
    "foot_model_conflict": 0, "foot_asia_direction": -1,
    "foot_asia_signal_strength": 0.0, "foot_euro_asia_conflict": False,
    "foot_euro_asia_conflict_score": 0.0,
}
d2 = judge.evaluate(make_request(f2))
print(f"  action: {d2.action}  tags: {d2.tags}")
print(f"  soft_count: {d2.trace.get('soft_reason_count')}  effective_threshold: {d2.trace.get('effective_observe_threshold')}")
all_pass &= check("action=OBSERVE", d2.action == DecisionAction.OBSERVE)
all_pass &= check("effective_threshold=2", d2.trace.get("effective_observe_threshold") == 2)
all_pass &= check("tag=foot_model_weak_agreement", "foot_model_weak_agreement" in d2.tags)

# ── 场景 3：极低一致性 + 1 个软冲突 → 强制 OBSERVE ───────────────────────────
section("场景 3: 极低一致性 (agreement=0.10) + 1 软冲突 → 强制 OBSERVE")
f3 = {**BASE,
    "lineup_known": False,          # 软冲突 1: LINEUP_UNKNOWN
    "foot_signals_available": True,
    "foot_model_agreement": 0.10,   # < critical=0.15 → 强制 OBSERVE
    "foot_model_consensus": 0, "foot_model_consensus_count": 3,
    "foot_model_conflict": 0, "foot_asia_direction": -1,
    "foot_asia_signal_strength": 0.0, "foot_euro_asia_conflict": False,
    "foot_euro_asia_conflict_score": 0.0,
}
d3 = judge.evaluate(make_request(f3))
print(f"  action: {d3.action}  tags: {d3.tags}")
print(f"  trace.foot_critical: {d3.trace.get('foot_critical')}")
all_pass &= check("action=OBSERVE", d3.action == DecisionAction.OBSERVE)
all_pass &= check("tag=foot_model_critical_disagreement", "foot_model_critical_disagreement" in d3.tags)
all_pass &= check("trace.foot_critical=True", d3.trace.get("foot_critical") is True)

# ── 场景 4：极低一致性 → ConflictDetector 自动产生 FOOT_MODEL_DISAGREEMENT ────
section("场景 4: 极低一致性 (agreement=0.10) → ConflictDetector 产生软冲突 → OBSERVE")
f4 = {**BASE,
    "foot_signals_available": True,
    "foot_model_agreement": 0.10,
    "foot_model_consensus": 0, "foot_model_consensus_count": 3,
    "foot_model_conflict": 0, "foot_asia_direction": -1,
    "foot_asia_signal_strength": 0.0, "foot_euro_asia_conflict": False,
    "foot_euro_asia_conflict_score": 0.0,
}
d4 = judge.evaluate(make_request(f4))
print(f"  action: {d4.action}  tags: {d4.tags}")
print(f"  soft_count: {d4.trace.get('soft_reason_count')}  effective_threshold: {d4.trace.get('effective_observe_threshold')}")
print(f"  reason_codes: {d4.reason_codes}")
# ConflictDetector 产生 FOOT_MODEL_DISAGREEMENT（1 软冲突）
# foot_critical=True → 有软冲突时强制 OBSERVE
all_pass &= check("action=OBSERVE（foot_critical + 软冲突）", d4.action == DecisionAction.OBSERVE)
all_pass &= check("FOOT_MODEL_DISAGREEMENT 触发", "FOOT_MODEL_DISAGREEMENT" in d4.reason_codes)
all_pass &= check("tag=foot_model_critical_disagreement", "foot_model_critical_disagreement" in d4.tags)

# ── 场景 5：无 foot 信号 → 向后兼容 ──────────────────────────────────────────
section("场景 5: 无 foot 信号 → 向后兼容")
f5 = {**BASE}  # 不含任何 foot_ 字段
d5 = judge.evaluate(make_request(f5))
print(f"  action: {d5.action}  tags: {d5.tags}")
print(f"  trace.foot_model_agreement: {d5.trace.get('foot_model_agreement')}")
all_pass &= check("action=APPROVE", d5.action == DecisionAction.APPROVE)
all_pass &= check("无 foot tags", not any(t.startswith("foot_") for t in d5.tags))
all_pass &= check("trace.foot_model_agreement=None", d5.trace.get("foot_model_agreement") is None)

# ── 场景 6：真实历史数据端到端 ────────────────────────────────────────────────
section("场景 6: 真实历史数据端到端")
try:
    import pymysql, pymysql.cursors
    from c1.features import build_governance_feature_fields

    conn = pymysql.connect(host="127.0.0.1", port=3306, user="root",
        password="Meta.123", database="foot", charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor)
    cur = conn.cursor()
    cur.execute("""
        SELECT mh.Id, mh.MainTeamId, mh.GuestTeamId, DATE(mh.MatchDate) as md
        FROM t_match_his mh
        INNER JOIN t_asia_his ah ON ah.MatchId = mh.Id
        INNER JOIN t_euro_his eh ON eh.MatchId = mh.Id
        WHERE mh.MainTeamGoals >= 0
        ORDER BY mh.MatchDate DESC LIMIT 1
    """)
    row = cur.fetchone()
    conn.close()

    raw = {
        "home_team": row["MainTeamId"], "away_team": row["GuestTeamId"],
        "match_date": str(row["md"]), "match_id": row["Id"],
        "odds_home": 2.20, "odds_draw": 3.10, "odds_away": 2.80,
        "opening_odds_home": 2.15, "opening_odds_draw": 3.20, "opening_odds_away": 2.90,
        "home_rating": 1500.0, "away_rating": 1450.0,
        "lineup_known": False, "predicted_side": "home", "market_side": "home",
    }
    gov_fields = build_governance_feature_fields(raw, enrich_foot=True)
    snap = FeatureSnapshot(match_id=row["Id"], feature_version="test", fields=gov_fields)
    pred = PredictionSnapshot(
        model_name="xgboost_v0",
        raw_probabilities={"home": 0.55, "draw": 0.25, "away": 0.20},
        predicted_side="home", confidence=0.65,
    )
    req = GovernanceRequest(match_id=row["Id"], feature_snapshot=snap, prediction_snapshot=pred)
    decision = judge.evaluate(req)

    print(f"  比赛: {row['MainTeamId']} vs {row['GuestTeamId']} ({row['md']})")
    print(f"  foot_model_agreement : {gov_fields.get('foot_model_agreement')}")
    print(f"  action               : {decision.action}")
    print(f"  tags                 : {decision.tags}")
    print(f"  reason_codes         : {decision.reason_codes}")
    print(f"  trace.foot_confirmed : {decision.trace.get('foot_confirmed')}")
    print(f"  trace.foot_weak      : {decision.trace.get('foot_weak')}")
    print(f"  trace.foot_critical  : {decision.trace.get('foot_critical')}")
    print(f"  effective_threshold  : {decision.trace.get('effective_observe_threshold')}")
    all_pass &= check("trace 含 foot_model_agreement", "foot_model_agreement" in decision.trace)

except Exception as e:
    print(f"  ⚠️  跳过（{e}）")

# ── 总结 ──────────────────────────────────────────────────────────────────────
section("测试总结")
if all_pass:
    print("✅ 所有测试通过")
    print()
    print("foot_model_agreement 对 Governance 决策的影响：")
    print("  agreement >= 0.75  → tag: foot_model_confirmed（规则模型支持预测）")
    print("  agreement < 0.30   → observe 阈值 3→2（更容易触发 OBSERVE）")
    print("                       tag: foot_model_weak_agreement")
    print("  agreement < 0.15   → 有软冲突时强制 OBSERVE")
    print("                       tag: foot_model_critical_disagreement")
    print("  无 foot 信号        → 行为与原来完全一致（向后兼容）")
else:
    print("❌ 部分测试失败")
    sys.exit(1)
