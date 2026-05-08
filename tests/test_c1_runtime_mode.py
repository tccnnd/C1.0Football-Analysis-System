from __future__ import annotations

import shutil
import sys
import unittest
import uuid
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from c1.runtime.mode import get_default_ui_filter, get_runtime_mode, is_release_gate_active


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


if __name__ == "__main__":
    unittest.main()
