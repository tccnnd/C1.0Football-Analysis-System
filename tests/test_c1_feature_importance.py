from c1.audit.feature_importance import (
    feature_quality_report,
    multiclass_accuracy,
    multiclass_logloss,
    rank_feature_report,
    samples_to_xy,
)


def test_samples_to_xy_uses_feature_order_and_filters_invalid_rows() -> None:
    samples = [
        {"label": 0, "features": {"a": 1, "b": 2}},
        {"label": 9, "features": {"a": 3, "b": 4}},
        {"label": 2, "features": {"a": 5}},
        {"label": 1, "features": "bad"},
    ]

    x_rows, labels = samples_to_xy(samples, ["a", "b"])

    assert x_rows == [[1.0, 2.0], [5.0, 0.0]]
    assert labels == [0, 2]


def test_feature_quality_report_counts_zero_and_unique_values() -> None:
    report = feature_quality_report(
        [
            {"features": {"a": 0, "b": 1}},
            {"features": {"a": 2, "b": 1}},
        ],
        ["a", "b"],
    )

    assert report["sample_count"] == 2
    assert report["features"]["a"]["zero_rate"] == 0.5
    assert report["features"]["b"]["unique_count"] == 1


def test_multiclass_metrics_are_computed_from_probabilities() -> None:
    probabilities = [[0.8, 0.1, 0.1], [0.3, 0.4, 0.3]]
    labels = [0, 2]

    assert multiclass_accuracy(probabilities, labels) == 0.5
    assert multiclass_logloss(probabilities, labels) > 0.0


def test_rank_feature_report_orders_low_score_features_first() -> None:
    ranked = rank_feature_report(
        feature_order=["weak", "strong"],
        built_in={
            "weak": {"gain": 0.0, "weight": 0.0},
            "strong": {"gain": 2.0, "weight": 10.0},
        },
        permutation={
            "features": {
                "weak": {"logloss_delta": 0.0, "accuracy_delta": 0.0},
                "strong": {"logloss_delta": 0.5, "accuracy_delta": -0.1},
            }
        },
        quality={"features": {"weak": {"zero_rate": 1.0}, "strong": {"zero_rate": 0.0}}},
    )

    assert [item["feature"] for item in ranked] == ["weak", "strong"]
