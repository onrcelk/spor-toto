import pytest

from sportoto.calibration import brier_score_multiclass, log_loss_score, reliability_bins


def test_calibration_scores_are_finite():
    probabilities = [[0.7, 0.2, 0.1], [0.2, 0.5, 0.3], [0.1, 0.2, 0.7]]
    labels = [0, 1, 2]
    assert brier_score_multiclass(probabilities, labels) == pytest.approx(0.22)
    assert log_loss_score(probabilities, labels) > 0


def test_reliability_bins_report_counts():
    result = reliability_bins([[0.8, 0.1, 0.1], [0.4, 0.3, 0.3]], [0, 1], bins=2)
    assert sum(row["count"] for row in result["class_0"]) == 2
    assert "class_1" in result
