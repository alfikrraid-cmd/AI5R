"""
MWO-RAE-000G -- RepositoryScanner: discovers repository files without
reading their contents. Consumes the existing, canonical
REPOSITORY_ARCHAEOLOGY.config.scanner_config.ScannerConfig unmodified
(Chief Architect ruling on MWO-RAE-000G) -- this module owns no
configuration shape of its own.

Per Chief Architect directive: "The default ignore directories and
supported extensions belong to RepositoryScanner as implementation
defaults, not to ScannerConfig itself." When ScannerConfig's
ignored_directories/supported_extensions are empty (its own defaults),
RepositoryScanner applies its own built-in default policies below.

No parsing, no metadata extraction, no hashing, no SQLite, no search.
The scanner never reads file contents -- only pathlib metadata
(is_dir/is_file/is_symlink/suffix/stat().st_size).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from REPOSITORY_ARCHAEOLOGY.config.scanner_config import ScannerConfig
from REPOSITORY_ARCHAEOLOGY.scan_statistics import ScanStatistics
from REPOSITORY_ARCHAEOLOGY.scanner_exception import (
    InvalidRepositoryError,
    RepositoryAccessDeniedError,
    RepositoryNotFoundError,
)

DEFAULT_IGNORED_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        "coverage",
        ".pytest_cache",
    }
)

DEFAULT_SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".py", ".md", ".json", ".yaml", ".yml", ".jsx", ".ts", ".tsx"}
)


@dataclass(frozen=True, slots=True)
class RepositoryRoot:
    """Immutable, validated repository root path."""

    path: Path

    def __post_init__(self) -> None:
        if not isinstance(self.path, Path):
            raise TypeError("path must be a pathlib.Path")

        try:
            exists = self.path.exists()
        except PermissionError as exc:
            raise RepositoryAccessDeniedError(
                f"Repository root is not accessible: {self.path}"
            ) from exc

        if not exists:
            raise RepositoryNotFoundError(f"Repository root not found: {self.path}")

        if not self.path.is_dir():
            raise InvalidRepositoryError(f"Repository root is not a directory: {self.path}")


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Immutable record describing one discovered repository file."""

    path: Path
    relative_path: Path
    extension: str
    size_bytes: int


@dataclass(frozen=True, slots=True)
class RepositorySnapshot:
    """Immutable aggregate result of one completed RepositoryScanner run."""

    root: RepositoryRoot
    results: tuple[ScanResult, ...]
    statistics: ScanStatistics


@dataclass
class _ScanCounters:
    """Private mutable accumulator scoped to a single scan() call."""

    directories_ignored: int = 0
    symlinks_ignored: int = 0
    files_ignored_by_extension: int = 0


class RepositoryScanner:
    """Discovers repository files. Never reads file contents, computes
    hashes, or parses anything."""

    def __init__(self, config: ScannerConfig | None = None) -> None:
        self._config = config or ScannerConfig()
        self._ignored_directories = (
            frozenset(self._config.ignored_directories)
            if self._config.ignored_directories
            else DEFAULT_IGNORED_DIRECTORIES
        )
        self._supported_extensions = (
            frozenset(self._config.supported_extensions)
            if self._config.supported_extensions
            else DEFAULT_SUPPORTED_EXTENSIONS
        )

    def scan(self, root: RepositoryRoot) -> RepositorySnapshot:
        if not isinstance(root, RepositoryRoot):
            raise TypeError("root must be a RepositoryRoot")

        counters = _ScanCounters()
        results: list[ScanResult] = []

        for file_path in self._iter_candidate_files(root.path, counters):
            extension = file_path.suffix.lower()

            if extension not in self._supported_extensions:
                counters.files_ignored_by_extension += 1
                continue

            results.append(
                ScanResult(
                    path=file_path,
                    relative_path=file_path.relative_to(root.path),
                    extension=extension,
                    size_bytes=file_path.stat().st_size,
                )
            )

        statistics = ScanStatistics(
            files_discovered=len(results),
            files_ignored_by_extension=counters.files_ignored_by_extension,
            directories_ignored=counters.directories_ignored,
            symlinks_ignored=counters.symlinks_ignored,
        )

        return RepositorySnapshot(root=root, results=tuple(results), statistics=statistics)

    def _iter_candidate_files(self, directory: Path, counters: _ScanCounters) -> Iterator[Path]:
        for entry in sorted(directory.iterdir(), key=lambda p: p.name):
            if entry.is_symlink() and not self._config.follow_symlinks:
                counters.symlinks_ignored += 1
                continue

            if entry.is_dir():
                if entry.name in self._ignored_directories:
                    counters.directories_ignored += 1
                    continue

                if self._config.recursive_scan:
                    yield from self._iter_candidate_files(entry, counters)

                continue

            if entry.is_file():
                yield entry


__all__ = ["RepositoryRoot", "ScanResult", "RepositorySnapshot", "RepositoryScanner"]
