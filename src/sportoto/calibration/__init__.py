"""Calibration application and evaluation metrics."""
from __future__ import annotations

import math
from typing import Sequence

from .model import Calibrator, IdentityCalibrator, validate_probabilities


def brier_score_multiclass(probabilities: Sequence[Sequence[float]], labels: Sequence[int]) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be non-empty and have equal length")
    return sum(sum((float(p) - (1.0 if i == label else 0.0)) ** 2 for i, p in enumerate(row)) for row, label in zip(probabilities, labels)) / len(labels)


def log_loss_score(probabilities: Sequence[Sequence[float]], labels: Sequence[int], epsilon: float = 1e-15) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be non-empty and have equal length")
    return sum(-math.log(max(float(row[label]), epsilon)) for row, label in zip(probabilities, labels)) / len(labels)


def reliability_bins(probabilities: Sequence[Sequence[float]], labels: Sequence[int], bins: int = 10) -> dict[str, list[dict[str, float | int]]]:
    if bins < 1 or len(probabilities) != len(labels):
        raise ValueError("bins must be positive and probabilities/labels must have equal length")
    classes = len(probabilities[0]) if probabilities else 0
    output = {}
    for class_index in range(classes):
        buckets = [[] for _ in range(bins)]
        for row, label in zip(probabilities, labels):
            probability = float(row[class_index])
            buckets[min(int(probability * bins), bins - 1)].append((probability, int(label == class_index)))
        output[f"class_{class_index}"] = [{"bin": i, "count": len(values), "mean_probability": sum(p for p, _ in values) / len(values) if values else 0.0, "accuracy": sum(y for _, y in values) / len(values) if values else 0.0} for i, values in enumerate(buckets)]
    return output


__all__ = ["Calibrator", "IdentityCalibrator", "brier_score_multiclass", "log_loss_score", "reliability_bins", "validate_probabilities"]
