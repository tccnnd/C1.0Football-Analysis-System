from xgb_ablation_matrix import _select_features, _train_test_split, build_ablation_matrix


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

    def fake_evaluate_feature_set(*, train_samples, test_samples, feature_order):
        return {
            "trained": True,
            "train_count": len(train_samples),
            "test_count": len(test_samples),
            "feature_count": len(feature_order),
            "logloss": 1.0 + len(feature_order) / 100.0,
            "accuracy": 0.5,
        }

    monkeypatch.setattr("xgb_ablation_matrix.evaluate_feature_set", fake_evaluate_feature_set)

    report = build_ablation_matrix(
        samples_path=samples_path,
        limit=4,
        train_ratio=0.5,
        seed=1,
        windows=[("test", "2017-01-01", "2018-01-01")],
        groups={"drop_market": ["market_home"]},
    )

    assert report["version"] == "xgb_ablation_matrix.v1"
    assert len(report["cells"]) == 1
    assert report["cells"][0]["ablated"]["feature_count"] == 37
    assert "logloss_delta" in report["cells"][0]["ablated"]
