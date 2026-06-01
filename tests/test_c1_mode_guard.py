from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.runtime.mode import (
    evaluate_c1_primary_acceptance,
    get_provider_guard_policy,
    get_runtime_mode,
)


class C1ModeGuardTests(unittest.TestCase):
    """c1_primary 验收门槛防回归测试。"""

    def _write_config(self, tmp_path: Path, mode: str, validation: dict | None) -> Path:
        payload: dict = {"mode": mode}
        if validation is not None:
            payload["switch_log"] = {"validation": validation}
        config_file = tmp_path / "runtime_mode.yaml"
        config_file.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")
        return config_file

    def setUp(self) -> None:
        self.tmp = PROJECT_ROOT / "data" / "tmp_c1_mode_tests"
        self.tmp.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_c1_primary_downgraded_when_accuracy_below_v24(self) -> None:
        cfg = self._write_config(
            self.tmp,
            "c1_primary",
            {"accuracy_c1": 0.497, "accuracy_v24": 0.503, "governance_separation": 0.08},
        )
        self.assertEqual(get_runtime_mode(cfg), "formal_list_default")

    def test_c1_primary_downgraded_when_separation_below_threshold(self) -> None:
        cfg = self._write_config(
            self.tmp,
            "c1_primary",
            {"accuracy_c1": 0.52, "accuracy_v24": 0.50, "governance_separation": 0.049},
        )
        self.assertEqual(get_runtime_mode(cfg), "formal_list_default")

    def test_c1_primary_downgraded_when_validation_missing(self) -> None:
        cfg = self._write_config(self.tmp, "c1_primary", None)
        self.assertEqual(get_runtime_mode(cfg), "formal_list_default")

    def test_c1_primary_honored_when_all_criteria_met(self) -> None:
        cfg = self._write_config(
            self.tmp,
            "c1_primary",
            {"accuracy_c1": 0.52, "accuracy_v24": 0.50, "governance_separation": 0.06},
        )
        self.assertEqual(get_runtime_mode(cfg), "c1_primary")

    def test_non_primary_mode_unaffected(self) -> None:
        cfg = self._write_config(self.tmp, "formal_list_default", None)
        self.assertEqual(get_runtime_mode(cfg), "formal_list_default")

    def test_evaluate_reports_unmet_criteria(self) -> None:
        result = evaluate_c1_primary_acceptance(
            {"switch_log": {"validation": {"accuracy_c1": 0.497, "accuracy_v24": 0.503, "governance_separation": 0.049}}}
        )
        self.assertFalse(result["accepted"])
        self.assertEqual(len(result["unmet"]), 2)

    # ── provider guard 绕过口防回归 ──────────────────────────────────
    def _config_with_validation(self, validation: dict) -> dict:
        return {
            "mode": "c1_primary",
            "switch_log": {"validation": validation},
            "guard_rails": {
                "default_provider_policy": {
                    "c1_primary": "fail_close",
                    "formal_list_default": "fail_close",
                },
            },
        }

    def test_provider_guard_downgrades_explicit_c1_primary_when_unmet(self) -> None:
        cfg = self._config_with_validation(
            {"accuracy_c1": 0.497, "accuracy_v24": 0.503, "governance_separation": 0.049}
        )
        result = get_provider_guard_policy(
            "api_football_primary", runtime_mode="c1_primary", config=cfg
        )
        # 显式传入 c1_primary 但验收失败 → 必须降级
        self.assertEqual(result["runtime_mode"], "formal_list_default")
        self.assertEqual(result.get("mode_downgraded_from"), "c1_primary")

    def test_provider_guard_honors_explicit_c1_primary_when_met(self) -> None:
        cfg = self._config_with_validation(
            {"accuracy_c1": 0.52, "accuracy_v24": 0.50, "governance_separation": 0.06}
        )
        result = get_provider_guard_policy(
            "api_football_primary", runtime_mode="c1_primary", config=cfg
        )
        self.assertEqual(result["runtime_mode"], "c1_primary")
        self.assertNotIn("mode_downgraded_from", result)

    def test_provider_guard_non_primary_mode_not_affected(self) -> None:
        cfg = self._config_with_validation(
            {"accuracy_c1": 0.497, "accuracy_v24": 0.503, "governance_separation": 0.049}
        )
        result = get_provider_guard_policy(
            "api_football_primary", runtime_mode="formal_list_default", config=cfg
        )
        self.assertEqual(result["runtime_mode"], "formal_list_default")
        self.assertNotIn("mode_downgraded_from", result)


if __name__ == "__main__":
    unittest.main()
