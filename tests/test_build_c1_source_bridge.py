from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
SCRIPTS_ROOT = PROJECT_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from build_c1_source_bridge import _norm, _team_match


class BuildC1SourceBridgeTests(unittest.TestCase):
    def test_norm_folds_diacritics(self) -> None:
        self.assertEqual(_norm("Greuther Fürth"), "greutherfurth")
        self.assertEqual(_norm("  San Diego FC "), "sandiegofc")

    def test_team_match_contains(self) -> None:
        candidate = {
            "teams": {
                "home": {"name": "SV Elversberg"},
                "away": {"name": "Hannover 96"},
            }
        }
        self.assertTrue(_team_match(candidate, home_alias="Elversberg", away_alias="Hannover 96"))
        self.assertFalse(_team_match(candidate, home_alias="Paderborn", away_alias="Hannover 96"))


if __name__ == "__main__":
    unittest.main()
