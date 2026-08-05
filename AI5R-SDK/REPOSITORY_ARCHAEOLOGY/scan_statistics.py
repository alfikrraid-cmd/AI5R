"""
MWO-RAE-000G -- ScanStatistics: immutable counters describing one
completed RepositoryScanner run. Pure data, no collection logic --
RepositoryScanner accumulates these counts and constructs the final
instance once a scan completes.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(frozen=True, slots=True)
class ScanStatistics:
    """Immutable summary counters for a single scan."""

    files_discovered: int
    files_ignored_by_extension: int
    directories_ignored: int
    symlinks_ignored: int

    def __post_init__(self) -> None:
        for f in fields(self):
            value = getattr(self, f.name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{f.name} must be a non-negative integer")


__all__ = ["ScanStatistics"]
