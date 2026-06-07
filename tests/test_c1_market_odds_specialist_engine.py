from c1.inference.engines.market_odds_specialist import MARKET_IMPLIED_FEATURES, MarketOddsSpecialist
from c1.inference.schema import InferenceInput


def test_market_odds_specialist_uses_market_implied_features() -> None:
    engine = MarketOddsSpecialist()
    result = engine.predict(
        InferenceInput(
            match_id="m1",
            odds_home=2.0,
            odds_draw=3.2,
            odds_away=4.0,
            home_rating=1500.0,
            away_rating=1500.0,
            feature_fields={"market_home": 0.52, "market_draw": 0.29, "market_away": 0.19},
        )
    )

    assert result.predicted_side == "home"
    assert result.probabilities == {"home": 0.52, "draw": 0.29, "away": 0.19}
    assert result.metadata["source"] == "market_implied_features"
    assert result.metadata["feature_count"] == len(MARKET_IMPLIED_FEATURES)


def test_market_odds_specialist_falls_back_to_odds_implied() -> None:
    engine = MarketOddsSpecialist()
    result = engine.predict(
        InferenceInput(
            match_id="m1",
            odds_home=2.0,
            odds_draw=4.0,
            odds_away=4.0,
            home_rating=1500.0,
            away_rating=1500.0,
            feature_fields={},
        )
    )

    assert result.predicted_side == "home"
    assert result.metadata["source"] == "odds_implied_fallback"
    assert round(sum(result.probabilities.values()), 6) == 1.0


def test_market_odds_specialist_reports_disagreement() -> None:
    engine = MarketOddsSpecialist()
    result = engine.predict(
        InferenceInput(
            match_id="m1",
            odds_home=2.0,
            odds_draw=3.2,
            odds_away=4.0,
            home_rating=1500.0,
            away_rating=1500.0,
            feature_fields={"market_home": 0.5, "market_draw": 0.3, "market_away": 0.2},
        ),
        reference_probabilities={"home": 0.3, "draw": 0.3, "away": 0.4},
    )

    assert result.disagreement == 0.2
    assert 0.0 < result.entropy <= 1.0
