"""
ConflictDetector foot 信号集成测试

覆盖三种场景：
1. 欧亚联动冲突（A1 核心信号）
2. 亚赔方向对抗模型预测
3. foot 多模型共识与 C1.0 不一致
4. 真实历史数据端到端
"""
import sys
sys.path.insert(0, "src")

from c1.core.schema import FeatureSnapshot, PredictionSnapshot, GovernanceRequest
from c1.core.reason_codes import ReasonCode, ReasonSeverity
from c1.modules.judge import ConflictDetector, load_governance_config, GovernanceJudge

cfg = load_governance_config()
detector = ConflictDetector()

def make_request(fields: dict, predicted_side: str = "home", confidence: float = 0.65) -> GovernanceRequest:
    snap = FeatureSnapshot(
        match_id="test_001",
        feature_version="test",
        fields=fields,
    )
    pred = PredictionSnapshot(
        model_name="xgboost_v0",
        raw_probabilities={"home": 0.55, "draw": 0.25, "away": 0.20},
        predicted_side=predicted_side,
        confidence=confidence,
    )
    return GovernanceRequest(
        match_id="test_001",
        feature_snapshot=snap,
        prediction_snapshot=pred,
    )

def section(t): print(f"\n{'='*60}\n  {t}\n{'='*60}")
def check(label, condition):
    icon = "✅" if condition else "❌"
    print(f"  {icon} {label}")
    return condition

all_pass = True

# ── 场景 1：欧亚联动冲突（软）────────────────────────────────────────────────
section("场景 1: 欧亚联动冲突（软冲突）")
fields_1 = {
    "predicted_side": "home",
    "market_side": "home",
    "market_divergence": 0.05,
    "injury_conflict_score": 0.0,
    "foot_signals_available": True,
    "foot_euro_asia_conflict": True,
    "foot_euro_asia_conflict_score": 0.55,   # 超过 soft=0.40
    "foot_euro_direction": 3,
    "foot_asia_direction": 0,
    "foot_asia_direction_consensus": 0.55,
    "foot_asia_signal_strength": 0.30,
    "foot_model_agreement": 0.5,
    "foot_model_consensus": -1,
    "foot_model_consensus_count": 0,
    "foot_model_conflict": 0,
    "foot_asia_let_ball_move": 0.0,
}
result_1 = detector.evaluate(make_request(fields_1), cfg)
print(f"  status: {result_1.status}")
codes_1 = [r.code for r in result_1.reasons]
print(f"  reason codes: {[c.value for c in codes_1]}")
all_pass &= check("status=WARN", result_1.status == "WARN")
all_pass &= check("FOOT_EURO_ASIA_CONFLICT 触发", ReasonCode.FOOT_EURO_ASIA_CONFLICT in codes_1)
all_pass &= check("severity=SOFT", all(r.severity == ReasonSeverity.SOFT for r in result_1.reasons))

# ── 场景 2：欧亚联动冲突（硬）────────────────────────────────────────────────
section("场景 2: 欧亚联动冲突（硬冲突）")
fields_2 = dict(fields_1)
fields_2["foot_euro_asia_conflict_score"] = 0.85   # 超过 hard=0.75
fields_2["foot_asia_direction_consensus"] = 0.85
result_2 = detector.evaluate(make_request(fields_2), cfg)
print(f"  status: {result_2.status}")
codes_2 = [r.code for r in result_2.reasons]
print(f"  reason codes: {[c.value for c in codes_2]}")
all_pass &= check("status=FAIL", result_2.status == "FAIL")
all_pass &= check("FOOT_EURO_ASIA_CONFLICT 触发", ReasonCode.FOOT_EURO_ASIA_CONFLICT in codes_2)
all_pass &= check("severity=HARD", any(r.severity == ReasonSeverity.HARD for r in result_2.reasons))

# ── 场景 3：亚赔方向对抗模型 ─────────────────────────────────────────────────
section("场景 3: 亚赔方向对抗模型预测")
fields_3 = {
    "predicted_side": "home",
    "market_side": "home",
    "market_divergence": 0.05,
    "injury_conflict_score": 0.0,
    "foot_signals_available": True,
    "foot_euro_asia_conflict": False,
    "foot_euro_asia_conflict_score": 0.0,
    "foot_euro_direction": -1,
    "foot_asia_direction": 0,          # 亚赔利客
    "foot_asia_direction_consensus": 0.80,
    "foot_asia_signal_strength": 0.60, # 超过 soft=0.45
    "foot_model_agreement": 0.5,
    "foot_model_consensus": -1,
    "foot_model_consensus_count": 0,
    "foot_model_conflict": 0,
    "foot_asia_let_ball_move": -0.25,
}
result_3 = detector.evaluate(make_request(fields_3, predicted_side="home"), cfg)
print(f"  status: {result_3.status}")
codes_3 = [r.code for r in result_3.reasons]
print(f"  reason codes: {[c.value for c in codes_3]}")
for r in result_3.reasons:
    print(f"    [{r.severity}] {r.message}")
all_pass &= check("status=WARN", result_3.status == "WARN")
all_pass &= check("FOOT_ASIA_SIGNAL_AGAINST_MODEL 触发", ReasonCode.FOOT_ASIA_SIGNAL_AGAINST_MODEL in codes_3)

# ── 场景 4：foot 多模型共识与 C1.0 不一致 ────────────────────────────────────
section("场景 4: foot 多模型共识与 C1.0 不一致")
fields_4 = {
    "predicted_side": "home",
    "market_side": "home",
    "market_divergence": 0.05,
    "injury_conflict_score": 0.0,
    "foot_signals_available": True,
    "foot_euro_asia_conflict": False,
    "foot_euro_asia_conflict_score": 0.0,
    "foot_euro_direction": -1,
    "foot_asia_direction": -1,
    "foot_asia_direction_consensus": 0.0,
    "foot_asia_signal_strength": 0.0,
    "foot_model_agreement": 0.15,      # 低于 disagreement_soft=0.30
    "foot_model_consensus": 0,         # foot 模型认为客胜
    "foot_model_consensus_count": 2,
    "foot_model_conflict": 0,
    "foot_asia_let_ball_move": 0.0,
}
result_4 = detector.evaluate(make_request(fields_4, predicted_side="home"), cfg)
print(f"  status: {result_4.status}")
codes_4 = [r.code for r in result_4.reasons]
print(f"  reason codes: {[c.value for c in codes_4]}")
for r in result_4.reasons:
    print(f"    [{r.severity}] {r.message}")
all_pass &= check("status=WARN", result_4.status == "WARN")
all_pass &= check("FOOT_MODEL_DISAGREEMENT 触发", ReasonCode.FOOT_MODEL_DISAGREEMENT in codes_4)

# ── 场景 5：无 foot 信号，不影响原有逻辑 ─────────────────────────────────────
section("场景 5: 无 foot 信号（向后兼容）")
fields_5 = {
    "predicted_side": "home",
    "market_side": "home",
    "market_divergence": 0.05,
    "injury_conflict_score": 0.0,
    # 不含任何 foot_ 字段
}
result_5 = detector.evaluate(make_request(fields_5), cfg)
print(f"  status: {result_5.status}")
all_pass &= check("status=PASS（无 foot 信号不影响）", result_5.status == "PASS")
all_pass &= check("无 foot reason codes", not any(
    c in [r.code for r in result_5.reasons]
    for c in [ReasonCode.FOOT_EURO_ASIA_CONFLICT,
              ReasonCode.FOOT_ASIA_SIGNAL_AGAINST_MODEL,
              ReasonCode.FOOT_MODEL_DISAGREEMENT]
))

# ── 场景 6：真实历史数据端到端（GovernanceJudge 完整流程）────────────────────
section("场景 6: 真实历史数据端到端")
try:
    import pymysql, pymysql.cursors
    from c1.features import build_governance_feature_fields
    from c1.core.schema import FeatureSnapshot, PredictionSnapshot

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
        "home_team": row["MainTeamId"],
        "away_team": row["GuestTeamId"],
        "match_date": str(row["md"]),
        "match_id": row["Id"],
        "odds_home": 2.20, "odds_draw": 3.10, "odds_away": 2.80,
        "opening_odds_home": 2.15, "opening_odds_draw": 3.20, "opening_odds_away": 2.90,
        "home_rating": 1500.0, "away_rating": 1450.0,
        "lineup_known": False,
        "predicted_side": "home",
        "market_side": "away",          # 故意设置市场方向相反，触发冲突
        "market_divergence": 0.08,
    }

    gov_fields = build_governance_feature_fields(raw, enrich_foot=True)
    snap = FeatureSnapshot(match_id=row["Id"], feature_version="test", fields=gov_fields)
    pred = PredictionSnapshot(
        model_name="xgboost_v0",
        raw_probabilities={"home": 0.55, "draw": 0.25, "away": 0.20},
        predicted_side="home",
        confidence=0.65,
    )
    req = GovernanceRequest(match_id=row["Id"], feature_snapshot=snap, prediction_snapshot=pred)

    judge = GovernanceJudge()
    decision = judge.evaluate(req)

    print(f"  比赛: {row['MainTeamId']} vs {row['GuestTeamId']} ({row['md']})")
    print(f"  foot_signals_available: {gov_fields.get('foot_signals_available')}")
    print(f"  foot_asia_direction   : {gov_fields.get('foot_asia_direction')}")
    print(f"  foot_euro_asia_conflict: {gov_fields.get('foot_euro_asia_conflict')}")
    print(f"  Governance action     : {decision.action}")
    print(f"  Gate statuses         : {decision.trace.get('gate_statuses')}")
    print(f"  Reason codes          : {decision.reason_codes}")
    print(f"  Tags                  : {decision.tags}")

    # ConflictDetector 的 metrics 应包含 foot 字段
    cd_result = next(g for g in decision.gate_results if g.gate == "ConflictDetector")
    all_pass &= check("ConflictDetector metrics 含 foot 字段",
        "foot_asia_direction" in cd_result.metrics or not gov_fields.get("foot_signals_available"))

except Exception as e:
    print(f"  ⚠️  跳过（{e}）")

# ── 总结 ──────────────────────────────────────────────────────────────────────
section("测试总结")
if all_pass:
    print("✅ 所有测试通过")
    print()
    print("ConflictDetector 现在检测三种 foot 冲突：")
    print("  1. FOOT_EURO_ASIA_CONFLICT      欧亚联动冲突（A1 核心信号）")
    print("  2. FOOT_ASIA_SIGNAL_AGAINST_MODEL  亚赔方向对抗模型预测")
    print("  3. FOOT_MODEL_DISAGREEMENT      foot 规则模型与 C1.0 不一致")
else:
    print("❌ 部分测试失败")
    sys.exit(1)
