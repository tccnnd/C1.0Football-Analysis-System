"""
Tests for accuracy improvement fixes in c1/inference layer.

Fix 1: Confidence formula - 0.85*top + 0.15*margin (was 0.65*top + 0.35*margin)
Fix 2: Default ensemble weights - market 0.25, elo 0.35, poisson 0.25, xgb 0.15
Fix 3: XGBoost fallback excluded from ensemble blend
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from c1.inference.runtime import _confidence
from c1.inference.calibration import DEFAULT_ENSEMBLE_WEIGHTS, _normalize_weights


class ConfidenceFormulaTests(unittest.TestCase):
    """Fix 1: confidence = 0.85*top + 0.15*margin"""

    def _old_confidence(self, top: float, margin: float) -> float:
        return min(1.0, max(0.0, 0.65 * top + 0.35 * margin))

    def _new_confidence(self, top: float, margin: float) -> float:
        return min(1.0, max(0.0, 0.85 * top + 0.15 * margin))

    def test_confidence_closer_to_top_prob(self):
        """新公式的置信度应更接近top概率，不再系统性压缩。"""
        probs = {"home": 0.68, "draw": 0.20, "away": 0.12}
        _, conf, margin = _confidence(probs)
        top = 0.68
        # 新公式: 0.85*0.68 + 0.15*0.48 = 0.578 + 0.072 = 0.650
        self.assertAlmostEqual(conf, 0.85 * top + 0.15 * margin, places=4)

    def test_new_formula_higher_than_old(self):
        """对于所有正常概率分布，新公式应高于旧公式。"""
        test_cases = [
            {"home": 0.68, "draw": 0.20, "away": 0.12},
            {"home": 0.55, "draw": 0.25, "away": 0.20},
            {"home": 0.80, "draw": 0.12, "away": 0.08},
            {"home": 0.45, "draw": 0.30, "away": 0.25},
        ]
        for probs in test_cases:
            _, conf_new, margin = _confidence(probs)
            top = max(probs.values())
            conf_old = self._old_confidence(top, margin)
            self.assertGreater(
                conf_new, conf_old,
                f"新公式应高于旧公式: top={top}, margin={margin}, old={conf_old}, new={conf_new}"
            )

    def test_high_confidence_threshold_reachable(self):
        """top=0.68时，新公式置信度应能超过0.65的高准策略门槛。"""
        probs = {"home": 0.68, "draw": 0.20, "away": 0.12}
        _, conf, _ = _confidence(probs)
        self.assertGreaterEqual(conf, 0.65,
            f"top=0.68时置信度{conf:.4f}应>=0.65，否则高准策略无法触发")

    def test_old_formula_fails_threshold(self):
        """验证旧公式在top=0.68时确实低于0.65（这是问题所在）。"""
        top, margin = 0.68, 0.48
        conf_old = self._old_confidence(top, margin)
        self.assertLess(conf_old, 0.65,
            f"旧公式{conf_old:.4f}应<0.65，确认问题存在")

    def test_confidence_monotone_with_top_prob(self):
        """置信度应随top概率单调递增。"""
        tops = [0.40, 0.50, 0.60, 0.70, 0.80]
        confs = []
        for top in tops:
            draw = (1.0 - top) * 0.6
            away = 1.0 - top - draw
            probs = {"home": top, "draw": draw, "away": away}
            _, conf, _ = _confidence(probs)
            confs.append(conf)
        for i in range(len(confs) - 1):
            self.assertLess(confs[i], confs[i + 1],
                f"置信度应单调递增: conf[{i}]={confs[i]:.4f} >= conf[{i+1}]={confs[i+1]:.4f}")

    def test_predicted_side_is_max_prob(self):
        """predicted_side应始终是概率最高的一方。"""
        cases = [
            ({"home": 0.60, "draw": 0.25, "away": 0.15}, "home"),
            ({"home": 0.20, "draw": 0.50, "away": 0.30}, "draw"),
            ({"home": 0.15, "draw": 0.25, "away": 0.60}, "away"),
        ]
        for probs, expected_side in cases:
            side, _, _ = _confidence(probs)
            self.assertEqual(side, expected_side)


class EnsembleWeightTests(unittest.TestCase):
    """Fix 2: market=0.25, elo=0.35, poisson=0.25, xgboost=0.15"""

    def test_market_weight_reduced(self):
        """市场权重应从0.35降至0.25。"""
        self.assertEqual(DEFAULT_ENSEMBLE_WEIGHTS["market"], 0.25)

    def test_elo_weight_increased(self):
        """ELO权重应从0.30升至0.35。"""
        self.assertEqual(DEFAULT_ENSEMBLE_WEIGHTS["elo"], 0.35)

    def test_poisson_weight_increased(self):
        """Poisson权重应从0.20升至0.25。"""
        self.assertEqual(DEFAULT_ENSEMBLE_WEIGHTS["poisson"], 0.25)

    def test_xgboost_weight_unchanged(self):
        """XGBoost权重保持0.15不变。"""
        self.assertEqual(DEFAULT_ENSEMBLE_WEIGHTS["xgboost"], 0.15)

    def test_weights_sum_to_one(self):
        """权重总和应为1.0。"""
        total = sum(DEFAULT_ENSEMBLE_WEIGHTS.values())
        self.assertAlmostEqual(total, 1.0, places=6)

    def test_market_not_dominant(self):
        """市场权重不应是最高权重（ELO应更高）。"""
        self.assertLess(
            DEFAULT_ENSEMBLE_WEIGHTS["market"],
            DEFAULT_ENSEMBLE_WEIGHTS["elo"],
            "市场权重不应高于ELO权重，否则模型无法找到市场定价错误"
        )

    def test_independent_models_outweigh_market(self):
        """ELO+Poisson的独立判断权重应超过市场权重。"""
        independent = DEFAULT_ENSEMBLE_WEIGHTS["elo"] + DEFAULT_ENSEMBLE_WEIGHTS["poisson"]
        market = DEFAULT_ENSEMBLE_WEIGHTS["market"]
        self.assertGreater(independent, market,
            f"独立模型权重{independent:.2f}应>市场权重{market:.2f}")

    def test_normalized_weights_consistent(self):
        """归一化后权重应与原始权重一致（因为总和已为1）。"""
        normalized = _normalize_weights(DEFAULT_ENSEMBLE_WEIGHTS)
        for key, val in DEFAULT_ENSEMBLE_WEIGHTS.items():
            self.assertAlmostEqual(normalized[key], val, places=5)


class XGBoostFallbackExclusionTests(unittest.TestCase):
    """Fix 3: XGBoost fallback时从ensemble排除"""

    def test_runtime_contains_fallback_exclusion_logic(self):
        """runtime.py应包含fallback排除逻辑。"""
        runtime_path = PROJECT_ROOT / "c1" / "inference" / "runtime.py"
        content = runtime_path.read_text(encoding="utf-8")
        self.assertIn("xgb_is_fallback", content,
            "runtime.py应检查xgb_fallback标志")
        self.assertIn("enable_xgboost = False", content,
            "fallback时应将enable_xgboost设为False以排除出blend_weights")

    def test_xgb_metadata_exposes_fallback_flag(self):
        """XGBoostProbabilityModel.predict应在metadata中暴露xgb_fallback标志。"""
        xgb_path = PROJECT_ROOT / "src" / "v24_app" / "models" / "xgboost_v0.py"
        content = xgb_path.read_text(encoding="utf-8")
        self.assertIn('"xgb_fallback"', content,
            "xgboost_v0.py应在metadata中包含xgb_fallback字段")
        self.assertIn("using_fallback", content,
            "应有using_fallback变量追踪是否使用了fallback")

    def test_fallback_flag_set_when_model_not_ready(self):
        """当模型未就绪时，xgb_fallback应为True。"""
        xgb_path = PROJECT_ROOT / "src" / "v24_app" / "models" / "xgboost_v0.py"
        content = xgb_path.read_text(encoding="utf-8")
        # 验证fallback逻辑：probs is None时using_fallback=True
        self.assertIn("using_fallback = probs is None", content)


class AccuracyImprovementIntegrationTests(unittest.TestCase):
    """集成验证：三个修复共同作用下的行为"""

    def test_high_prob_prediction_gets_high_confidence(self):
        """top=0.70时，置信度应>=0.65，能触发高准策略门槛。"""
        probs = {"home": 0.70, "draw": 0.18, "away": 0.12}
        _, conf, _ = _confidence(probs)
        self.assertGreaterEqual(conf, 0.65,
            f"top=0.70时置信度{conf:.4f}应>=0.65")

    def test_medium_prob_prediction_below_threshold(self):
        """top=0.50时，置信度应<0.55，不应触发高准策略。"""
        probs = {"home": 0.50, "draw": 0.28, "away": 0.22}
        _, conf, _ = _confidence(probs)
        self.assertLess(conf, 0.55,
            f"top=0.50时置信度{conf:.4f}应<0.55，避免低质量预测通过")

    def test_confidence_range_reasonable(self):
        """置信度应在[0, 1]范围内。"""
        test_cases = [
            {"home": 1.0, "draw": 0.0, "away": 0.0},
            {"home": 0.333, "draw": 0.333, "away": 0.334},
            {"home": 0.0, "draw": 0.0, "away": 1.0},
        ]
        for probs in test_cases:
            _, conf, _ = _confidence(probs)
            self.assertGreaterEqual(conf, 0.0)
            self.assertLessEqual(conf, 1.0)

    def test_elo_now_dominant_weight(self):
        """ELO应是权重最高的模型，体现独立判断优先。"""
        max_key = max(DEFAULT_ENSEMBLE_WEIGHTS, key=DEFAULT_ENSEMBLE_WEIGHTS.get)
        self.assertEqual(max_key, "elo",
            f"ELO应是权重最高的模型，当前最高是{max_key}")


if __name__ == "__main__":
    unittest.main()
