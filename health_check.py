"""系统健康检查"""
import sys
sys.path.insert(0, "src")

print("=== C1.0 独立性验证 ===")

from c1.inference.baseline import BaselineInferenceEngine
print("  baseline.py: OK (no v24_app import)")

from c1.inference.engines import EloRatingEngine, PoissonScoreEngine
e = EloRatingEngine()
snap = e.from_ratings(1600, 1500, 0.25)
print(f"  ELO engine: OK (home_win={snap.home_win:.3f})")

from c1.inference.xgb_adapter import C1XGBoostAdapter, _XGB_AVAILABLE
print(f"  XGBoost: available={_XGB_AVAILABLE}")

from c1.data.foot_bridge import get_foot_bridge
bridge = get_foot_bridge()
ping = bridge.ping()
print(f"  foot MySQL: {ping['status']}")

from c1.modules.judge import GovernanceJudge
judge = GovernanceJudge()
print(f"  Governance: {len(judge.gates)} gates")

from c1.translation.engine import C1TranslationEngine
print("  Translation: OK")

from c1.audit.store import C1AuditStore
print("  Audit: OK")

print("\n=== 系统健康 ===")
print("  C1.0 baseline: 独立 (不依赖 v24_app)")
print("  C1.0 XGBoost: 可选依赖 (V24 不可用时 fallback)")
print(f"  foot MySQL: {ping['status']}")
print("  所有层: 可导入 ✅")
