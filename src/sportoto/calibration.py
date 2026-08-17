"""Probability calibration metrics for multi-class football predictions."""
from __future__ import annotations

import math
from typing import Sequence


def brier_score_multiclass(probabilities: Sequence[Sequence[float]], labels: Sequence[int]) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be non-empty and have equal length")
    total = 0.0
    for row, label in zip(probabilities, labels):
        if label < 0 or label >= len(row):
            raise ValueError("label is outside probability row")
        total += sum((float(p) - (1.0 if i == label else 0.0)) ** 2 for i, p in enumerate(row))
    return total / len(labels)


def log_loss_score(probabilities: Sequence[Sequence[float]], labels: Sequence[int], epsilon: float = 1e-15) -> float:
    if len(probabilities) != len(labels) or not probabilities:
        raise ValueError("probabilities and labels must be non-empty and have equal length")
    return sum(-math.log(max(float(row[label]), epsilon)) for row, label in zip(probabilities, labels)) / len(labels)


def reliability_bins(probabilities: Sequence[Sequence[float]], labels: Sequence[int], bins: int = 10) -> dict[str, list[dict[str, float | int]]]:
    if bins < 1:
        raise ValueError("bins must be at least 1")
    if len(probabilities) != len(labels):
        raise ValueError("probabilities and labels must have equal length")
    classes = len(probabilities[0]) if probabilities else 0
    output: dict[str, list[dict[str, float | int]]] = {}
    for class_index in range(classes):
        buckets: list[list[tuple[float, int]]] = [[] for _ in range(bins)]
        for row, label in zip(probabilities, labels):
            probability = float(row[class_index])
            bucket = min(int(probability * bins), bins - 1)
            buckets[bucket].append((probability, int(label == class_index)))
        output[f"class_{class_index}"] = [
            {"bin": index, "count": len(values), "mean_probability": sum(p for p, _ in values) / len(values), "accuracy": sum(y for _, y in values) / len(values)}
            if values else {"bin": index, "count": 0, "mean_probability": 0.0, "accuracy": 0.0}
            for index, values in enumerate(buckets)
        ]
    return output


__all__ = ["brier_score_multiclass", "log_loss_score", "reliability_bins"]
