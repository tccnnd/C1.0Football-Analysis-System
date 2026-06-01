import json
import tempfile
import unittest
from pathlib import Path

from c1.data import load_elo_ratings, resolve_team_rating


class TestEloLoader(unittest.TestCase):
    def test_load_elo_ratings_from_file(self) -> None:
        """Test loading ELO ratings from a valid file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "data" / "state"
            state_dir.mkdir(parents=True)
            
            elo_file = state_dir / "elo_ratings.json"
            elo_file.write_text(
                json.dumps({
                    "updated_at": "2026-05-26 17:58:08",
                    "ratings": {
                        "曼联": 1756.25,
                        "曼城": 1871.46,
                        "利物浦": 1711.27,
                        "阿森纳": 1860.11,
                    }
                }),
                encoding="utf-8"
            )
            
            ratings = load_elo_ratings(root)
            self.assertEqual(ratings["曼联"], 1756.25)
            self.assertEqual(ratings["曼城"], 1871.46)
            self.assertEqual(ratings["利物浦"], 1711.27)
            self.assertEqual(ratings["阿森纳"], 1860.11)

    def test_load_elo_ratings_missing_file(self) -> None:
        """Test loading ELO ratings when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ratings = load_elo_ratings(root)
            self.assertEqual(ratings, {})

    def test_load_elo_ratings_malformed_json(self) -> None:
        """Test loading ELO ratings from malformed JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            state_dir = root / "data" / "state"
            state_dir.mkdir(parents=True)
            
            elo_file = state_dir / "elo_ratings.json"
            elo_file.write_text("not valid json", encoding="utf-8")
            
            ratings = load_elo_ratings(root)
            self.assertEqual(ratings, {})

    def test_resolve_team_rating_exact_match(self) -> None:
        """Test resolving team rating with exact match."""
        ratings = {
            "曼联": 1756.25,
            "曼城": 1871.46,
        }
        
        result = resolve_team_rating("曼联", ratings)
        self.assertEqual(result, 1756.25)

    def test_resolve_team_rating_case_insensitive_match(self) -> None:
        """Test resolving team rating with case-insensitive match."""
        ratings = {
            "Manchester United": 1756.25,
            "Manchester City": 1871.46,
        }
        
        result = resolve_team_rating("manchester united", ratings)
        self.assertEqual(result, 1756.25)

    def test_resolve_team_rating_not_found(self) -> None:
        """Test resolving team rating when team not found."""
        ratings = {
            "曼联": 1756.25,
        }
        
        result = resolve_team_rating("不存在的队伍", ratings, default=1500.0)
        self.assertEqual(result, 1500.0)

    def test_resolve_team_rating_empty_team_name(self) -> None:
        """Test resolving team rating with empty team name."""
        ratings = {"曼联": 1756.25}
        
        result = resolve_team_rating("", ratings, default=1500.0)
        self.assertEqual(result, 1500.0)


if __name__ == "__main__":
    unittest.main()
