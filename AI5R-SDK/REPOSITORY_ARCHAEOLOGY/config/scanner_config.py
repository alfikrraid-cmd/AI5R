"""
MWO-RAE-000H -- ScannerConfig: canonical, immutable configuration for
RepositoryScanner (not implemented by this MWO). Pure data, no loading
logic, no environment variable reading -- mirrors DOCUMENT_INGEST.
config.PipelineConfig's own "config is data, not behavior" discipline.
Dependency-free: no import of RepositoryScanner, ParserRegistry,
evidence objects, SQLite, or the search engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ScannerConfig:
    supported_extensions: tuple[str, ...] = ()
    ignored_directories: tuple[str, ...] = ()
    follow_symlinks: bool = False
    recursive_scan: bool = True


__all__ = ["ScannerConfig"]
