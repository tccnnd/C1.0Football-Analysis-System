"""
Unit tests for HT/FT translation module.
"""

import pytest
from c1.translation.htft_translator import (
    estimate_ht_probabilities,
    estimate_expected_goals,
    generate_htft_outcomes,
    translate_htft,
)


class TestEstimateHTProabilities:
    """Test HT probability estimation."""

    def test_ht_probabilities_sum_to_one(self):
        """HT probabilities should sum to 1.0."""
        ht_probs = estimate_ht_probabilities(0.4, 0.3, 0.3)
        total = sum(ht_probs.values())
        assert abs(total - 1.0) < 0.01

    def test_ht_probabilities_lower_than_ft(self):
        """HT probabilities should be lower variance than FT."""
        ft_home = 0.5
        ft_away = 0.2
        ft_draw = 0.3
        
        ht_probs = estimate_ht_probabilities(ft_home, ft_away, ft_draw, ht_scaling=0.45)
        
        # HT draw should be higher (less decisive)
        assert ht_probs["draw"] > ft_draw

    def test_ht_probabilities_with_different_scaling(self):
        """Different scaling factors should produce different results."""
        ft_home = 0.4
        ft_away = 0.3
        ft_draw = 0.3
        
        ht_probs_low = estimate_ht_probabilities(ft_home, ft_away, ft_draw, ht_scaling=0.30)
        ht_probs_high = estimate_ht_probabilities(ft_home, ft_away, ft_draw, ht_scaling=0.60)
        
        # Higher scaling should produce higher side probabilities
        assert ht_probs_high["home"] > ht_probs_low["home"]


class TestEstimateExpectedGoals:
    """Test expected goals estimation."""

    def test_expected_goals_positive(self):
        """Expected goals should be positive."""
        home_xg, away_xg = estimate_expected_goals(0.5, 0.3, 0.2)
        assert home_xg > 0
        assert away_xg > 0

    def test_expected_goals_home_advantage(self):
        """Home team should have higher expected goals when favored."""
        home_xg, away_xg = estimate_expected_goals(0.6, 0.2, 0.2)
        assert home_xg > away_xg

    def test_expected_goals_elo_adjustment(self):
        """ELO rating difference should affect expected goals."""
        home_xg_equal, away_xg_equal = estimate_expected_goals(0.5, 0.3, 0.2, 1500, 1500)
        home_xg_strong, away_xg_strong = estimate_expected_goals(0.5, 0.3, 0.2, 1700, 1500)
        
        # Stronger home team should have higher expected goals
        assert home_xg_strong > home_xg_equal


class TestGenerateHTFTOutcomes:
    """Test HT/FT outcome generation."""

    def test_htft_outcomes_sum_to_one(self):
        """HT/FT outcomes should sum to 1.0."""
        ht_probs = {"home": 0.35, "draw": 0.40, "away": 0.25}
        ft_probs = {"home": 0.40, "draw": 0.35, "away": 0.25}
        
        outcomes = generate_htft_outcomes(ht_probs, ft_probs)
        total = sum(outcomes.values())
        assert abs(total - 1.0) < 0.01

    def test_htft_outcomes_count(self):
        """Should generate up to 9 outcomes."""
        ht_probs = {"home": 0.35, "draw": 0.40, "away": 0.25}
        ft_probs = {"home": 0.40, "draw": 0.35, "away": 0.25}
        
        outcomes = generate_htft_outcomes(ht_probs, ft_probs, min_probability=0.0)
        assert len(outcomes) == 9

    def test_htft_outcomes_filtering(self):
        """Low probability outcomes should be filtered."""
        ht_probs = {"home": 0.35, "draw": 0.40, "away": 0.25}
        ft_probs = {"home": 0.40, "draw": 0.35, "away": 0.25}
        
        outcomes_all = generate_htft_outcomes(ht_probs, ft_probs, min_probability=0.0)
        outcomes_filtered = generate_htft_outcomes(ht_probs, ft_probs, min_probability=0.05)
        
        assert len(outcomes_filtered) <= len(outcomes_all)

    def test_htft_best_outcome(self):
        """Best outcome should be HT/FT with highest probability."""
        ht_probs = {"home": 0.6, "draw": 0.2, "away": 0.2}
        ft_probs = {"home": 0.6, "draw": 0.2, "away": 0.2}
        
        outcomes = generate_htft_outcomes(ht_probs, ft_probs)
        best = max(outcomes.items(), key=lambda x: x[1])
        
        # Best outcome should be HOME/HOME
        assert best[0] == "HOME/HOME"


class TestTranslateHTFT:
    """Test HT/FT translation."""

    def test_translate_htft_active_status(self):
        """Should translate with ACTIVE status."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
        )
        
        assert result.play == "htft"
        assert result.status == "ACTIVE"
        assert result.selection is not None

    def test_translate_htft_blocked_status(self):
        """Should not translate with BLOCKED status."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="BLOCKED",
        )
        
        assert result.play == "htft"
        assert result.status == "BLOCKED"
        assert result.selection is None

    def test_translate_htft_low_confidence(self):
        """Should not translate with low confidence."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.20,
            governance_status="ACTIVE",
            config={"min_confidence": 0.35},
        )
        
        assert result.selection is None
        assert "model_confidence_below_threshold" in result.rationale

    def test_translate_htft_with_elo_ratings(self):
        """Should use ELO ratings in translation."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
            home_rating=1700.0,
            away_rating=1500.0,
        )
        
        assert result.play == "htft"
        assert "home_expected_goals" in result.evidence or "ht_probabilities" in result.evidence

    def test_translate_htft_evidence_complete(self):
        """Evidence should include all necessary fields."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
        )
        
        assert "ft_probabilities" in result.evidence
        assert "ht_probabilities" in result.evidence
        assert "htft_outcomes" in result.evidence
        assert "best_outcome" in result.evidence
        assert "best_outcome_probability" in result.evidence

    def test_translate_htft_tags(self):
        """Should include appropriate tags."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
        )
        
        assert "htft_translation" in result.tags
        assert "poisson_based" in result.tags


class TestHTFTIntegration:
    """Integration tests for HT/FT translation."""

    def test_htft_translation_pipeline(self):
        """Test complete HT/FT translation pipeline."""
        # Simulate a match with clear home advantage
        raw_probs = {"home": 0.55, "draw": 0.30, "away": 0.15}
        confidence = 0.70
        
        result = translate_htft(
            raw_probabilities=raw_probs,
            confidence=confidence,
            governance_status="ACTIVE",
            home_rating=1650.0,
            away_rating=1500.0,
        )
        
        # Should produce a valid translation
        assert result.play == "htft"
        assert result.status == "ACTIVE"
        assert result.selection is not None
        assert result.confidence == round(confidence, 6)
        assert len(result.rationale) > 0
        assert len(result.evidence) > 0

    def test_htft_translation_downgraded(self):
        """Test HT/FT translation with DOWNGRADED status."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="DOWNGRADED",
        )
        
        assert result.status == "DOWNGRADED"
        assert result.selection is not None  # Should still translate

    def test_htft_translation_shadow(self):
        """Test HT/FT translation with SHADOW status."""
        result = translate_htft(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="SHADOW",
        )
        
        assert result.status == "SHADOW"
        assert result.selection is not None  # Should still translate


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
