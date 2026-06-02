"""将校准结果写入系统配置"""
import json
from pathlib import Path

ROOT = Path(__file__).parent

# 1. 更新 ensemble 权重
weights_file = ROOT / "data" / "models" / "ensemble_weights_v1.json"
weights_file.parent.mkdir(parents=True, exist_ok=True)

existing = {}
if weights_file.exists():
    try:
        existing = json.loads(weights_file.read_text(encoding="utf-8"))
    except Exception:
        existing = {}

existing["weights"] = {
    "market": 0.278,
    "elo": 0.333,
    "poisson": 0.167,
    "xgboost": 0.15,
    "dixon_coles": 0.222,
}
existing["calibrated_at"] = "2026-05-29"
existing["source"] = "calibrate_strategy.py grid_search (8000 matches)"
existing["baseline_accuracy"] = 0.518
existing["optimized_accuracy"] = 0.526

weights_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"1. Ensemble 权重已更新: {weights_file}")
print(f"   {existing['weights']}")

# 2. 更新 play thresholds（2串1 置信度门槛）
thresholds_file = ROOT / "data" / "models" / "play_thresholds_v1.json"
thresholds = {}
if thresholds_file.exists():
    try:
        thresholds = json.loads(thresholds_file.read_text(encoding="utf-8"))
    except Exception:
        thresholds = {}

# 更新 2串1 相关阈值
thresholds["parlay_min_confidence"] = 0.55
thresholds["parlay_max_odds"] = 2.00
thresholds["parlay_exclude_draw"] = True
thresholds["parlay_weekday_max"] = 1
thresholds["parlay_weekend_max"] = 3
thresholds["parlay_high_accuracy_confidence"] = 0.60
thresholds["calibrated_at"] = "2026-05-29"

thresholds_file.write_text(json.dumps(thresholds, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n2. 2串1 阈值已更新: {thresholds_file}")
print(f"   parlay_min_confidence: 0.55")
print(f"   parlay_max_odds: 2.00")
print(f"   parlay_weekday_max: 1")
print(f"   parlay_weekend_max: 3")

# 3. 验证
print("\n3. 验证配置文件:")
for f in [weights_file, thresholds_file, ROOT / "c1/configs/parlay_strategy_cfg.yaml"]:
    if f.exists():
        print(f"   ✅ {f.name} ({f.stat().st_size} bytes)")
    else:
        print(f"   ❌ {f.name} 不存在")

print("\n✅ 校准结果已写入系统配置")
print("\n生产环境策略:")
print("  工作日（5场）: 最多 1 个 2串1，conf>=0.55, odds<=2.00")
print("  周末（25+场）: 最多 3 个 2串1，conf>=0.55, odds<=2.00")
print("  高准模式:      conf>=0.60, odds<=2.20")
print("  不选平局，不选杯赛")
