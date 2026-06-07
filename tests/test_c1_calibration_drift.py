from c1.audit.calibration_drift import build_calibration_drift_report, build_model_calibration_report


def test_model_calibration_report_computes_core_metrics() -> None:
    rows = [
        {
            "actual": "home",
            "c1_probabilities": {"home": 0.7, "draw": 0.2, "away": 0.1},
            "c1_confidence": 0.7,
        },
        {
            "actual": "away",
            "c1_probabilities": {"home": 0.6, "draw": 0.2, "away": 0.2},
            "c1_confidence": 0.6,
        },
    ]

    report = build_model_calibration_report(
        rows,
        model_name="c1",
        probability_key="c1_probabilities",
        confidence_key="c1_confidence",
    )

    assert report["count"] == 2
    assert report["accuracy"] == 0.5
    assert report["avg_confidence"] == 0.65
    assert report["calibration_gap"] == -0.15
    assert report["ece"] >= 0.0
    assert report["brier"] > 0.0
    assert report["logloss"] > 0.0
    assert report["buckets"]


def test_calibration_drift_report_compares_c1_and_v24() -> None:
    rows = [
        {
            "actual": "home",
            "v24_probabilities": {"home": 0.55, "draw": 0.25, "away": 0.20},
            "v24_confidence": 0.55,
            "c1_probabilities": {"home": 0.70, "draw": 0.20, "away": 0.10},
            "c1_confidence": 0.70,
        },
        {
            "actual": "away",
            "v24_probabilities": {"home": 0.30, "draw": 0.20, "away": 0.50},
            "v24_confidence": 0.50,
            "c1_probabilities": {"home": 0.60, "draw": 0.20, "away": 0.20},
            "c1_confidence": 0.60,
        },
    ]

    report = build_calibration_drift_report(rows)

    assert report["version"] == "calibration_drift.v1"
    assert report["models"]["v24"]["count"] == 2
    assert report["models"]["c1"]["count"] == 2
    assert report["comparison"]["accuracy_delta"] == -0.5
    assert "brier_delta" in report["comparison"]


def test_calibration_report_ignores_rows_without_probabilities() -> None:
    report = build_calibration_drift_report(
        [
            {"actual": "home", "c1_confidence": 0.8},
            {"actual": "unknown", "c1_probabilities": {"home": 1.0, "draw": 0.0, "away": 0.0}},
        ]
    )

    assert report["models"]["c1"]["count"] == 0
    assert report["models"]["c1"]["ece"] is None
