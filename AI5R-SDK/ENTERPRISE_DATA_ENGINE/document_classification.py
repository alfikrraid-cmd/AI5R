from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentCandidate:
    document_type: str
    confidence: float
    matched_signals: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "matched_signals", tuple(self.matched_signals))


@dataclass(frozen=True)
class DocumentClassification:
    worksheet_name: str
    primary_type: str
    confidence: float
    candidates: tuple[DocumentCandidate, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))


__all__ = ["DocumentCandidate", "DocumentClassification"]
