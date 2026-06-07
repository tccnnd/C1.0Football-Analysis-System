from market_odds_specialist_report import (
    MARKET_FEATURE_SETS,
    _validate_feature_sets,
    build_market_odds_specialist_matrix,
)


def test_validate_feature_sets_rejects_unknown_feature() -> None:
    try:
        _validate_feature_sets({"bad": ["market_home", "not_a_feature"]})
    except ValueError as exc:
        assert "not_a_feature" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_market_feature_sets_are_market_scoped() -> None:
    assert "market_implied_core" in MARKET_FEATURE_SETS
    assert "market_home" in MARKET_FEATURE_SETS["market_implied_core"]
    assert "home_rating" not in MARKET_FEATURE_SETS["market_implied_core"]


def test_build_market_odds_specialist_matrix_with_fake_evaluator(tmp_path, monkeypatch) -> None:
    samples_path = tmp_path / "samples.json"
    samples_path.write_text(
        '{"items": ['
        '{"timestamp":"2017-01-01","label":0,"features":{"market_home":1}},'
        '{"timestamp":"2017-01-02","label":1,"features":{"market_draw":1}},'
        '{"timestamp":"2017-01-03","label":2,"features":{"market_away":1}},'
        '{"timestamp":"2017-01-04","label":0,"features":{"market_home":1}}'
        "]}",
        encoding="utf-8",
    )

    def fake_evaluate_feature_set(*, train_samples, test_samples, feature_order, seed=42):
        return {
            "trained": True,
            "train_count": len(train_samples),
            "test_count": len(test_samples),
            "feature_count": len(feature_order),
            "logloss": 1.0 + len(feature_order) / 100.0,
            "accuracy": 0.5,
            "brier": 0.2 + len(feature_order) / 1000.0,
            "ece": 0.1 + len(feature_order) / 1000.0,
            "calibration_gap": -0.05,
        }

    monkeypatch.setattr("market_odds_specialist_report.evaluate_feature_set", fake_evaluate_feature_set)

    report = build_market_odds_specialist_matrix(
        samples_path=samples_path,
        limit=4,
        train_ratio=0.5,
        seed=1,
        seeds=[1, 2],
        windows=[("test", "2017-01-01", "2018-01-01")],
        feature_sets={"market_core": ["market_home", "market_draw", "market_away"]},
    )

    assert report["version"] == "market_odds_specialist.v1"
    assert report["seeds"] == [1, 2]
    assert len(report["cells"]) == 1
    assert report["cells"][0]["specialist"]["trained_seed_count"] == 2
    assert report["cells"][0]["specialist"]["feature_count"] == 3
    assert "logloss_delta" in report["cells"][0]["specialist"]
    assert "brier_delta" in report["cells"][0]["specialist"]
