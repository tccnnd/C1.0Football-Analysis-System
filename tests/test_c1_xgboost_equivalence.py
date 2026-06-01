from __future__ import annotations

"""
XGBoost 独立化等价回归测试。

目的：证明 c1/inference/engines/xgboost_engine.py 与旧
v24_app.models.xgboost_v0.XGBoostProbabilityModel 对同一输入的行为一致：
- FEATURE_ORDER 完全相同
- feature map 关键字段一致
- 输出概率归一化，且与 V24 差异在阈值内

V24 不可用时整体跳过（不视为失败）。
"""

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c1.inference.engines.xgboost_engine import (
    FEATURE_ORDER as C1_FEATURE_ORDER,
    XGBoostInferenceEngine,
)
from c1.inference.schema import InferenceInput

try:
    from v24_app.models.xgboost_v0 import XGBoostProbabilityModel
    from v24_app.models.ensemble import EnsembleContext

    _V24_AVAILABLE = True
except Exception:  # pragma: no cover - 环境相关
    _V24_AVAILABLE = False


def _fixture_fields() -> dict:
    return {
        "match_time": "19:35",
        "match_date": "2026-04-04",  # Saturday → is_weekend=1
        "opening_odds_home": 1.82,
        "opening_odds_draw": 3.40,
        "opening_odds_away": 4.30,
        "return_rate": 0.92,
        "kelly_home": 0.95,
        "kelly_draw": 0.93,
        "kelly_away": 0.98,
        "home_recent_match_count": 6,
        "away_recent_match_count": 6,
        "home_recent_points_pg": 2.2,
        "away_recent_points_pg": 1.1,
        "recent_points_diff": 1.1,
        "home_recent_goal_diff_pg": 0.9,
        "away_recent_goal_diff_pg": -0.2,
        "recent_goal_diff_diff": 1.1,
        "home_recent_goals_for_pg": 1.8,
        "away_recent_goals_for_pg": 0.9,
        "home_recent_win_rate": 0.6,
        "away_recent_win_rate": 0.2,
    }


def _c1_input() -> InferenceInput:
    return InferenceInput(
        match_id="2026-04-04|friendly|A|B",
        odds_home=1.88,
        odds_draw=3.35,
        odds_away=4.10,
        home_rating=1530.0,
        away_rating=1488.0,
        league_strength=0.92,
        feature_fields=_fixture_fields(),
        metadata={},
    )


def _v24_context():
    fields = _fixture_fields()
    oh, od, oa = 1.88, 3.35, 4.10
    ih, idr, ia = 1.0 / oh, 1.0 / od, 1.0 / oa
    tot = ih + idr + ia
    market_probs = (ih / tot, idr / tot, ia / tot)
    metadata = {
        "match_id": "2026-04-04|friendly|A|B",
        "odds_home": oh,
        "odds_draw": od,
        "odds_away": oa,
        **fields,
    }
    return EnsembleContext(
        market_probs=market_probs,
        home_rating=1530.0,
        away_rating=1488.0,
        market_draw_prob=market_probs[1],
        league_strength=0.92,
        metadata=metadata,
    )


@unittest.skipUnless(_V24_AVAILABLE, "v24_app not importable; equivalence comparison skipped")
class XGBoostEquivalenceTests(unittest.TestCase):
    def test_feature_order_identical(self) -> None:
        self.assertEqual(C1_FEATURE_ORDER, XGBoostProbabilityModel.FEATURE_ORDER)

    def test_feature_map_key_fields_match(self) -> None:
        c1_engine = XGBoostInferenceEngine(PROJECT_ROOT)
        c1_map = c1_engine._feature_map(_c1_input())

        v24_model = XGBoostProbabilityModel(PROJECT_ROOT)
        v24_map = v24_model._feature_map(_v24_context())

        # 每个 FEATURE_ORDER 字段的值都应一致（浮点容差）
        for name in C1_FEATURE_ORDER:
            self.assertIn(name, c1_map, f"c1 缺少特征 {name}")
            self.assertIn(name, v24_map, f"v24 缺少特征 {name}")
            self.assertAlmostEqual(
                float(c1_map[name]), float(v24_map[name]), places=4,
                msg=f"特征 {name} 不一致: c1={c1_map[name]} v24={v24_map[name]}",
            )

    def test_feature_vector_identical(self) -> None:
        c1_engine = XGBoostInferenceEngine(PROJECT_ROOT)
        c1_map = c1_engine._feature_map(_c1_input())
        c1_vec = c1_engine._feature_vector(c1_map)

        v24_model = XGBoostProbabilityModel(PROJECT_ROOT)
        v24_map = v24_model._feature_map(_v24_context())
        v24_vec = v24_model._feature_vector(v24_map)

        self.assertEqual(len(c1_vec), len(v24_vec))
        for i, (a, b) in enumerate(zip(c1_vec, v24_vec)):
            self.assertAlmostEqual(a, b, places=4, msg=f"feature_vector[{i}] 不一致")

    def test_prediction_normalized_and_close(self) -> None:
        c1_engine = XGBoostInferenceEngine(PROJECT_ROOT)
        c1_out = c1_engine.predict(_c1_input())
        c1_probs = c1_out["probabilities"]

        v24_model = XGBoostProbabilityModel(PROJECT_ROOT)
        v24_out = v24_model.predict(_v24_context())
        v24_probs = v24_out.probabilities

        # 两者都应归一化
        self.assertAlmostEqual(sum(c1_probs), 1.0, places=5)
        self.assertAlmostEqual(sum(v24_probs), 1.0, places=5)

        # 同一 fixture 下，逐项差异应在阈值内（同模型产物 + 同特征 → 应近乎相同）
        for i in range(3):
            self.assertLess(
                abs(c1_probs[i] - v24_probs[i]), 0.02,
                msg=f"概率[{i}] 差异过大: c1={c1_probs[i]:.4f} v24={v24_probs[i]:.4f}",
            )

    def test_fallback_path_equivalent_when_model_absent(self) -> None:
        # 用不存在模型目录的临时 project_root 强制走 fallback 分支
        tmp_root = PROJECT_ROOT / "data" / "tmp_c1_xgb_equiv"
        (tmp_root / "data" / "models").mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp_root, ignore_errors=True))

        c1_engine = XGBoostInferenceEngine(tmp_root)
        c1_map = c1_engine._feature_map(_c1_input())
        c1_fb = c1_engine._fallback_probs(_c1_input(), c1_map)

        v24_model = XGBoostProbabilityModel(tmp_root)
        ctx = _v24_context()
        v24_map = v24_model._feature_map(ctx)
        v24_fb = v24_model._fallback_probs(ctx, v24_map)

        self.assertAlmostEqual(sum(c1_fb), 1.0, places=5)
        for i in range(3):
            self.assertAlmostEqual(c1_fb[i], v24_fb[i], places=4, msg=f"fallback 概率[{i}] 不一致")


if __name__ == "__main__":
    unittest.main()
