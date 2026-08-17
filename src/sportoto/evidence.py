"""Structured evidence records for pre-match reports and LLM synthesis."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

_ALLOWED_IMPACTS = {"supports_home", "supports_draw", "supports_away", "risk_only", "neutral"}


@dataclass(frozen=True)
class EvidenceRecord:
    match_id: str
    category: str
    claim: str
    value: Any
    source: str
    observed_at: str
    confidence: float
    impact: str

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.impact not in _ALLOWED_IMPACTS:
            raise ValueError(f"impact must be one of {sorted(_ALLOWED_IMPACTS)}")


@dataclass(frozen=True)
class EvidencePacket:
    match_id: str
    facts: list[EvidenceRecord]
    summary: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"match_id": self.match_id, "facts": [asdict(fact) for fact in self.facts], "summary": self.summary}


def evidence_packet(match_id: str, facts: list[EvidenceRecord], summary: str | None = None) -> EvidencePacket:
    return EvidencePacket(match_id=match_id, facts=facts, summary=summary)


__all__ = ["EvidencePacket", "EvidenceRecord", "evidence_packet"]
