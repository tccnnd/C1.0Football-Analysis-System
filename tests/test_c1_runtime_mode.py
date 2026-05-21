from __future__ import annotations

import shutil
import sys
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from c1.runtime.mode import get_default_ui_filter, get_provider_guard_policy, get_runtime_mode, is_release_gate_active


class C1RuntimeModeTests(unittest.TestCase):
    def make_config_dir(self) -> Path:
        base_dir = PROJECT_ROOT / "data" / "tmp_c1_runtime_mode_tests"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"case_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=False)
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def test_get_runtime_mode_reads_supported_mode(self) -> None:
        config_dir = self.make_config_dir()
        config_path = config_dir / "runtime_mode.yaml"
        config_path.write_text("mode: gate_only\n", encoding="utf-8")
        self.assertEqual(get_runtime_mode(config_path), "gate_only")

    def test_get_default_ui_filter_respects_formal_mode(self) -> None:
        self.assertEqual(get_default_ui_filter("formal_list_default", has_formal_rows=True), "正式建议")
        self.assertEqual(get_default_ui_filter("formal_list_default", has_formal_rows=False), "全部")
        self.assertEqual(get_default_ui_filter("shadow", has_formal_rows=True), "全部")

    def test_release_gate_active_only_for_gate_modes(self) -> None:
        self.assertFalse(is_release_gate_active("shadow"))
        self.assertTrue(is_release_gate_active("gate_only"))
        self.assertTrue(is_release_gate_active("formal_list_default"))

    def test_provider_guard_policy_resolves_by_runtime_mode(self) -> None:
        config_dir = self.make_config_dir()
        config_path = config_dir / "runtime_mode.yaml"
        config_path.write_text(
            "\n".join(
                [
                    "mode: shadow",
                    "guard_rails:",
                    "  default_provider_policy:",
                    "    shadow: fail_open",
                    "    gate_only: fail_close",
                    "    formal_list_default: fail_close",
                    "  providers:",
                    "    api_football_primary:",
                    "      shadow: fail_open",
                    "      gate_only: fail_close",
                    "      formal_list_default: fail_close",
                ]
            ),
            encoding="utf-8",
        )
        shadow_policy = get_provider_guard_policy(
            "api_football_primary",
            runtime_mode="shadow",
            path=config_path,
        )
        formal_policy = get_provider_guard_policy(
            "api_football_primary",
            runtime_mode="formal_list_default",
            path=config_path,
        )
        fallback_policy = get_provider_guard_policy(
            "unknown_provider",
            runtime_mode="shadow",
            path=config_path,
        )
        self.assertEqual(shadow_policy["policy"], "fail_open")
        self.assertEqual(formal_policy["policy"], "fail_close")
        self.assertEqual(fallback_policy["policy"], "fail_open")

    def test_provider_guard_policy_empty_config_uses_mode_fallback(self) -> None:
        policy = get_provider_guard_policy(
            "crawler_fallback",
            runtime_mode="gate_only",
            config={},
        )
        self.assertEqual(policy["policy"], "fail_close")
        self.assertEqual(policy["policy_source"], "fallback")


if __name__ == "__main__":
    unittest.main()
