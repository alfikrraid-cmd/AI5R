"""
MWO-RAE-000H -- SearchConfig: canonical, immutable configuration for
Repository Search (not implemented by this MWO). Pure data, no search
logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SearchConfig:
    case_sensitive: bool = False
    exact_match: bool = False
    max_results: int = 100

    def __post_init__(self) -> None:
        if self.max_results <= 0:
            raise ValueError("max_results must be a positive integer")


__all__ = ["SearchConfig"]
