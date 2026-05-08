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

from v24_app.core import _compute_live_source_health_score


class CoreSourceHealthTests(unittest.TestCase):
    def test_health_score_bounds(self) -> None:
        self.assertEqual(_compute_live_source_health_score(raw_count=0, valid_count=0, merged_count=0), 0)
        self.assertGreater(_compute_live_source_health_score(raw_count=10, valid_count=8, merged_count=10), 0)
        self.assertLessEqual(_compute_live_source_health_score(raw_count=10, valid_count=10, merged_count=10), 100)

    def test_health_score_penalizes_low_coverage(self) -> None:
        high_coverage = _compute_live_source_health_score(raw_count=10, valid_count=8, merged_count=8)
        low_coverage = _compute_live_source_health_score(raw_count=10, valid_count=8, merged_count=20)
        self.assertGreater(high_coverage, low_coverage)


if __name__ == "__main__":
    unittest.main()

