"""
Unit tests for scoreline translation module.
"""

import pytest
from c1.translation.scoreline_translator import (
    estimate_expected_goals,
    generate_score_matrix,
    filter_score_matrix,
    score_to_selection,
    translate_scoreline,
)


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

    def test_expected_goals_clamped(self):
        """Expected goals should be clamped to reasonable range."""
        home_xg, away_xg = estimate_expected_goals(0.99, 0.01, 0.0)
        
        # Should not exceed 4.0
        assert home_xg <= 4.0
        assert away_xg >= 0.3


class TestGenerateScoreMatrix:
    """Test score matrix generation."""

    def test_score_matrix_sum_to_one(self):
        """Score matrix probabilities should sum to 1.0."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        total = sum(matrix.values())
        assert abs(total - 1.0) < 0.01

    def test_score_matrix_size(self):
        """Score matrix should have correct size."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        # Should have (5+1) * (5+1) = 36 outcomes
        assert len(matrix) == 36

    def test_score_matrix_high_probability_scores(self):
        """High probability scores should be in matrix."""
        matrix = generate_score_matrix(2.0, 2.0, max_goals=5)
        
        # (2, 2) should have reasonable probability
        assert (2, 2) in matrix
        assert matrix[(2, 2)] > 0.05

    def test_score_matrix_low_probability_scores(self):
        """Very low probability scores should have low probability."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        
        # (5, 5) should have very low probability
        assert (5, 5) in matrix
        assert matrix[(5, 5)] < 0.01


class TestFilterScoreMatrix:
    """Test score matrix filtering."""

    def test_filter_by_probability(self):
        """Should filter scores below minimum probability."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        filtered = filter_score_matrix(matrix, min_probability=0.05)
        
        # All filtered scores should be >= 0.05
        for prob in filtered.values():
            assert prob >= 0.05

    def test_filter_by_max_outcomes(self):
        """Should limit to maximum number of outcomes."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        filtered = filter_score_matrix(matrix, min_probability=0.0, max_outcomes=10)
        
        assert len(filtered) <= 10

    def test_filter_renormalize(self):
        """Filtered matrix should sum to 1.0."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        filtered = filter_score_matrix(matrix, min_probability=0.02, max_outcomes=20)
        
        total = sum(filtered.values())
        assert abs(total - 1.0) < 0.01

    def test_filter_preserves_best_scores(self):
        """Filtering should preserve highest probability scores."""
        matrix = generate_score_matrix(1.5, 1.2, max_goals=5)
        best_unfiltered = max(matrix.items(), key=lambda x: x[1])
        
        filtered = filter_score_matrix(matrix, min_probability=0.01, max_outcomes=20)
        best_filtered = max(filtered.items(), key=lambda x: x[1])
        
        # Best score should be preserved
        assert best_unfiltered[0] == best_filtered[0]


class TestScoreToSelection:
    """Test score to selection conversion."""

    def test_score_to_selection_format(self):
        """Should format score correctly."""
        assert score_to_selection(2, 1) == "2-1"
        assert score_to_selection(0, 0) == "0-0"
        assert score_to_selection(3, 2) == "3-2"

    def test_score_to_selection_double_digit(self):
        """Should handle double-digit scores."""
        assert score_to_selection(10, 5) == "10-5"
        assert score_to_selection(5, 10) == "5-10"


class TestTranslateScoreline:
    """Test scoreline translation."""

    def test_translate_scoreline_active_status(self):
        """Should translate with ACTIVE status."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
        )
        
        assert result.play == "scoreline"
        assert result.status == "ACTIVE"
        assert result.selection is not None

    def test_translate_scoreline_blocked_status(self):
        """Should not translate with BLOCKED status."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="BLOCKED",
        )
        
        assert result.play == "scoreline"
        assert result.status == "BLOCKED"
        assert result.selection is None

    def test_translate_scoreline_low_confidence(self):
        """Should not translate with low confidence."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.20,
            governance_status="ACTIVE",
            config={"min_confidence": 0.35},
        )
        
        assert result.selection is None
        assert "model_confidence_below_threshold" in result.rationale

    def test_translate_scoreline_with_elo_ratings(self):
        """Should use ELO ratings in translation."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
            home_rating=1700.0,
            away_rating=1500.0,
        )
        
        assert result.play == "scoreline"
        assert "home_expected_goals" in result.evidence
        assert "away_expected_goals" in result.evidence

    def test_translate_scoreline_evidence_complete(self):
        """Evidence should include all necessary fields."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
        )
        
        assert "ft_probabilities" in result.evidence
        assert "home_expected_goals" in result.evidence
        assert "away_expected_goals" in result.evidence
        assert "score_matrix_size" in result.evidence
        assert "filtered_outcomes" in result.evidence
        assert "best_score" in result.evidence
        assert "best_score_probability" in result.evidence

    def test_translate_scoreline_tags(self):
        """Should include appropriate tags."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="ACTIVE",
        )
        
        assert "scoreline_translation" in result.tags
        assert "poisson_based" in result.tags


class TestScorelineIntegration:
    """Integration tests for scoreline translation."""

    def test_scoreline_translation_pipeline(self):
        """Test complete scoreline translation pipeline."""
        # Simulate a match with clear home advantage
        raw_probs = {"home": 0.55, "draw": 0.30, "away": 0.15}
        confidence = 0.70
        
        result = translate_scoreline(
            raw_probabilities=raw_probs,
            confidence=confidence,
            governance_status="ACTIVE",
            home_rating=1650.0,
            away_rating=1500.0,
        )
        
        # Should produce a valid translation
        assert result.play == "scoreline"
        assert result.status == "ACTIVE"
        assert result.selection is not None
        assert result.confidence == round(confidence, 6)
        assert len(result.rationale) > 0
        assert len(result.evidence) > 0

    def test_scoreline_translation_downgraded(self):
        """Test scoreline translation with DOWNGRADED status."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="DOWNGRADED",
        )
        
        assert result.status == "DOWNGRADED"
        assert result.selection is not None  # Should still translate

    def test_scoreline_translation_shadow(self):
        """Test scoreline translation with SHADOW status."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.5, "draw": 0.3, "away": 0.2},
            confidence=0.65,
            governance_status="SHADOW",
        )
        
        assert result.status == "SHADOW"
        assert result.selection is not None  # Should still translate

    def test_scoreline_selection_format(self):
        """Scoreline selection should be in correct format."""
        result = translate_scoreline(
            raw_probabilities={"home": 0.55, "draw": 0.30, "away": 0.15},
            confidence=0.70,
            governance_status="ACTIVE",
        )
        
        if result.selection:
            # Should be in format "X-Y"
            parts = result.selection.split("-")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1].isdigit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
