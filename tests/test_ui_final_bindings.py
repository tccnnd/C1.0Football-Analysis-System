from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

import v24_app.ui as ui


class UIFinalBindingsTests(unittest.TestCase):
    def test_key_bindings_point_to_final_functions(self) -> None:
        self.assertEqual(ui.FootballPredictionApp.open_user_center.__name__, "_app_open_user_center_final")
        self.assertEqual(ui.FootballPredictionApp.analyze_selected.__name__, "_app_analyze_selected_with_parlays")
        self.assertEqual(ui.FootballPredictionApp.analyze_all.__name__, "_app_analyze_all_with_parlays")
        self.assertEqual(ui.FootballPredictionApp.export_current_report.__name__, "_app_export_visible_report")
        self.assertEqual(ui.FootballPredictionApp.show_recent_settlements.__name__, "_app_show_recent_settlements_table")
        self.assertEqual(ui.FootballPredictionApp.settle_selected_result.__name__, "_app_settle_selected_result")
        self.assertEqual(ui.FootballPredictionApp._show_match_details.__name__, "_app_show_match_details_with_parlays")
        self.assertEqual(ui.FootballPredictionApp._apply_play_model_backtest_result.__name__, "_app_apply_play_model_backtest_result_v3")
        self.assertEqual(ui.FootballPredictionApp._apply_ensemble_backtest_result.__name__, "_app_apply_ensemble_backtest_result_v2")


if __name__ == "__main__":
    unittest.main()
