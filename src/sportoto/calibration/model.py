"""Fit-frozen probability calibrator contracts for production workflow."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

RESULTS = ("1", "X", "2")


def validate_probabilities(probabilities: dict[str, Any]) -> dict[str, float]:
    if set(probabilities) != set(RESULTS):
        raise ValueError("probabilities must contain exactly 1, X and 2")
    values = {key: float(probabilities[key]) for key in RESULTS}
    if any(value < 0.0 or value > 1.0 for value in values.values()):
        raise ValueError("probabilities must be between 0 and 1")
    total = sum(values.values())
    if total <= 0.0:
        raise ValueError("probabilities must have positive sum")
    return {key: value / total for key, value in values.items()}


class Calibrator(Protocol):
    @property
    def metadata(self) -> dict[str, Any]:
        ...

    def transform(self, probabilities: dict[str, float]) -> dict[str, float]:
        ...


@dataclass(frozen=True)
class IdentityCalibrator:
    version: str = "identity-1"
    fitted_until: str | None = None

    @property
    def metadata(self) -> dict[str, Any]:
        return {"method": "identity", "version": self.version, "fitted_until": self.fitted_until,
                "input": "model_predictions", "output": "calibrated_predictions"}

    def transform(self, probabilities: dict[str, float]) -> dict[str, float]:
        return validate_probabilities(probabilities)


__all__ = ["Calibrator", "IdentityCalibrator", "validate_probabilities"]
