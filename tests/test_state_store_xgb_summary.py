from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from v24_app.storage.state_store import StateStore


class StateStoreXgbSummaryTests(unittest.TestCase):
    def test_save_xgb_samples_writes_lightweight_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            store.save_xgb_samples(
                [
                    {
                        "features": {"market_home": 0.4},
                        "label": 0,
                        "meta": {"match_date": "2024-01-01", "league": "A", "source": "history"},
                    },
                    {
                        "features": {"market_home": 0.3},
                        "label": 1,
                        "meta": {"match_date": "2024-01-02", "league": "B", "source": "history"},
                    },
                    {
                        "features": {},
                        "label": 2,
                        "meta": {"match_date": "2024-01-03", "league": "A", "source": "live"},
                    },
                ]
            )

            summary = store.load_xgb_samples_summary(rebuild_if_stale=False)

        self.assertEqual(summary["sample_count"], 3)
        self.assertEqual(summary["valid_feature_count"], 3)
        self.assertEqual(summary["label_counts"], {"0": 1, "1": 1, "2": 1})
        self.assertEqual(summary["date_start"], "2024-01-01")
        self.assertEqual(summary["date_end"], "2024-01-03")
        self.assertEqual(summary["league_count"], 2)
        self.assertEqual(summary["source_counts"]["history"], 2)

    def test_load_xgb_samples_summary_rebuilds_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = StateStore(Path(tmp))
            store.save_xgb_samples([{"features": {"x": 1}, "label": 0, "meta": {"league": "A"}}])
            store.xgb_samples_summary_file.unlink()

            summary = store.load_xgb_samples_summary()

        self.assertEqual(summary["sample_count"], 1)
        self.assertEqual(summary["valid_feature_count"], 1)


if __name__ == "__main__":
    unittest.main()
