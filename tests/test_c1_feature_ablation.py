from xgb_ablation_matrix import _calibration_metrics, _multiclass_brier, _select_features, _train_test_split, build_ablation_matrix


def test_select_features_removes_excluded_names() -> None:
    assert _select_features(["a", "b", "c"], {"b"}) == ["a", "c"]


def test_train_test_split_is_deterministic() -> None:
    samples = [{"id": idx} for idx in range(10)]

    left_a, right_a = _train_test_split(samples, train_ratio=0.6, seed=7)
    left_b, right_b = _train_test_split(samples, train_ratio=0.6, seed=7)

    assert left_a == left_b
    assert right_a == right_b
    assert len(left_a) == 6
    assert len(right_a) == 4


def test_build_ablation_matrix_with_fake_evaluator_inputs(tmp_path, monkeypatch) -> None:
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
            "logloss": 1.0 + len(feature_order) / 100.0 + seed / 10000.0,
            "accuracy": 0.5 + seed / 10000.0,
            "brier": 0.2 + len(feature_order) / 1000.0,
            "ece": 0.1 + len(feature_order) / 1000.0,
            "calibration_gap": -0.05,
        }

    monkeypatch.setattr("xgb_ablation_matrix.evaluate_feature_set", fake_evaluate_feature_set)

    report = build_ablation_matrix(
        samples_path=samples_path,
        limit=4,
        train_ratio=0.5,
        seed=1,
        seeds=[1, 2],
        windows=[("test", "2017-01-01", "2018-01-01")],
        groups={"drop_market": ["market_home"]},
    )

    assert report["version"] == "xgb_ablation_matrix.v2"
    assert report["seeds"] == [1, 2]
    assert len(report["cells"]) == 1
    assert report["cells"][0]["ablated"]["feature_count"] == 37
    assert report["cells"][0]["ablated"]["trained_seed_count"] == 2
    assert "logloss_delta" in report["cells"][0]["ablated"]
    assert "brier_delta" in report["cells"][0]["ablated"]
    assert "ece_delta" in report["cells"][0]["ablated"]


def test_multiclass_brier_scores_probability_error() -> None:
    value = _multiclass_brier([[0.8, 0.1, 0.1], [0.2, 0.7, 0.1]], [0, 1])
    assert round(value, 6) == 0.033333


def test_calibration_metrics_report_ece_and_gap() -> None:
    metrics = _calibration_metrics([[0.8, 0.1, 0.1], [0.2, 0.7, 0.1]], [0, 2])
    assert metrics["ece"] > 0.0
    assert metrics["calibration_gap"] < 0.0
