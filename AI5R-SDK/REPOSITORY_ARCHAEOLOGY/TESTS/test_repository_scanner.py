import dataclasses
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from REPOSITORY_ARCHAEOLOGY.config.scanner_config import ScannerConfig
from REPOSITORY_ARCHAEOLOGY.repository_scanner import (
    RepositoryRoot,
    RepositoryScanner,
    RepositorySnapshot,
    ScanResult,
)
from REPOSITORY_ARCHAEOLOGY.scan_statistics import ScanStatistics
from REPOSITORY_ARCHAEOLOGY.scanner_exception import (
    InvalidRepositoryError,
    RepositoryAccessDeniedError,
    RepositoryNotFoundError,
)


def _symlinks_supported(tmp_path: Path) -> bool:
    target = tmp_path / "_symlink_capability_target.txt"
    target.write_text("x")
    link = tmp_path / "_symlink_capability_link.txt"
    try:
        link.symlink_to(target)
    except OSError:
        return False
    link.unlink()
    target.unlink()
    return True


# --- RepositoryRoot validation -------------------------------------------------


def test_repository_root_accepts_valid_directory(tmp_path):
    root = RepositoryRoot(path=tmp_path)

    assert root.path == tmp_path


def test_repository_root_rejects_missing_path(tmp_path):
    missing = tmp_path / "does-not-exist"

    with pytest.raises(RepositoryNotFoundError):
        RepositoryRoot(path=missing)


def test_repository_root_rejects_file_path(tmp_path):
    file_path = tmp_path / "not_a_dir.txt"
    file_path.write_text("x")

    with pytest.raises(InvalidRepositoryError):
        RepositoryRoot(path=file_path)


def test_repository_root_rejects_non_path_argument():
    with pytest.raises(TypeError):
        RepositoryRoot(path="not-a-path-object")


def test_repository_root_raises_access_denied_on_permission_error(tmp_path, monkeypatch):
    def _raise_permission_error(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "exists", _raise_permission_error)

    with pytest.raises(RepositoryAccessDeniedError):
        RepositoryRoot(path=tmp_path)


# --- Empty repository ------------------------------------------------------


def test_scan_empty_repository_returns_no_results(tmp_path):
    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    assert isinstance(snapshot, RepositorySnapshot)
    assert snapshot.results == ()
    assert snapshot.statistics.files_discovered == 0


# --- Extension filtering -----------------------------------------------------


def test_scan_discovers_supported_extension_files(tmp_path):
    (tmp_path / "module.py").write_text("x")
    (tmp_path / "README.md").write_text("x")
    (tmp_path / "image.png").write_bytes(b"\x00")

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    discovered_names = {r.relative_path.name for r in snapshot.results}
    assert discovered_names == {"module.py", "README.md"}
    assert snapshot.statistics.files_ignored_by_extension == 1


def test_scan_result_fields_are_correct(tmp_path):
    (tmp_path / "module.py").write_text("hello")

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)
    result = snapshot.results[0]

    assert isinstance(result, ScanResult)
    assert result.relative_path == Path("module.py")
    assert result.extension == ".py"
    assert result.size_bytes == len(b"hello")
    assert result.path == tmp_path / "module.py"


def test_scan_honors_injected_supported_extensions(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    (tmp_path / "module.py").write_text("x")

    root = RepositoryRoot(path=tmp_path)
    config = ScannerConfig(supported_extensions=(".txt",))
    scanner = RepositoryScanner(config=config)

    snapshot = scanner.scan(root)

    discovered_names = {r.relative_path.name for r in snapshot.results}
    assert discovered_names == {"notes.txt"}


# --- Ignored directories -----------------------------------------------------


def test_scan_ignores_default_directories(tmp_path):
    ignored_dir = tmp_path / "__pycache__"
    ignored_dir.mkdir()
    (ignored_dir / "cached.py").write_text("x")

    kept_dir = tmp_path / "src"
    kept_dir.mkdir()
    (kept_dir / "main.py").write_text("x")

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    discovered_names = {r.relative_path.name for r in snapshot.results}
    assert discovered_names == {"main.py"}
    assert snapshot.statistics.directories_ignored == 1


def test_scan_honors_injected_ignored_directories(tmp_path):
    custom_ignored = tmp_path / "vendor"
    custom_ignored.mkdir()
    (custom_ignored / "third_party.py").write_text("x")

    root = RepositoryRoot(path=tmp_path)
    config = ScannerConfig(ignored_directories=("vendor",))
    scanner = RepositoryScanner(config=config)

    snapshot = scanner.scan(root)

    assert snapshot.results == ()
    assert snapshot.statistics.directories_ignored == 1


# --- Nested directories / recursive_scan -------------------------------------


def test_scan_discovers_nested_directories(tmp_path):
    nested = tmp_path / "a" / "b" / "c"
    nested.mkdir(parents=True)
    (nested / "deep.py").write_text("x")

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    assert snapshot.results[0].relative_path == Path("a") / "b" / "c" / "deep.py"


def test_scan_respects_recursive_scan_false(tmp_path):
    (tmp_path / "top.py").write_text("x")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "deep.py").write_text("x")

    root = RepositoryRoot(path=tmp_path)
    config = ScannerConfig(recursive_scan=False)
    scanner = RepositoryScanner(config=config)

    snapshot = scanner.scan(root)

    discovered_names = {r.relative_path.name for r in snapshot.results}
    assert discovered_names == {"top.py"}


# --- Symbolic links -----------------------------------------------------------


def test_scan_ignores_symbolic_links_by_default(tmp_path):
    if not _symlinks_supported(tmp_path):
        pytest.skip("symlink creation not permitted in this environment")

    target = tmp_path / "target.py"
    target.write_text("x")
    link = tmp_path / "link.py"
    link.symlink_to(target)

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    discovered_names = {r.relative_path.name for r in snapshot.results}
    assert discovered_names == {"target.py"}
    assert snapshot.statistics.symlinks_ignored == 1


def test_scan_follows_symbolic_links_when_configured(tmp_path):
    if not _symlinks_supported(tmp_path):
        pytest.skip("symlink creation not permitted in this environment")

    target = tmp_path / "target.py"
    target.write_text("x")
    link = tmp_path / "link.py"
    link.symlink_to(target)

    root = RepositoryRoot(path=tmp_path)
    config = ScannerConfig(follow_symlinks=True)
    scanner = RepositoryScanner(config=config)

    snapshot = scanner.scan(root)

    discovered_names = {r.relative_path.name for r in snapshot.results}
    assert discovered_names == {"target.py", "link.py"}


# --- Statistics ----------------------------------------------------------------


def test_scan_statistics_are_collected(tmp_path):
    (tmp_path / "keep.py").write_text("x")
    (tmp_path / "skip.png").write_bytes(b"\x00")

    ignored_dir = tmp_path / "dist"
    ignored_dir.mkdir()
    (ignored_dir / "bundle.js").write_text("x")

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    stats = snapshot.statistics
    assert isinstance(stats, ScanStatistics)
    assert stats.files_discovered == 1
    assert stats.files_ignored_by_extension == 1
    assert stats.directories_ignored == 1


# --- Contracts / invariants -----------------------------------------------------


def test_scan_never_reads_file_contents(tmp_path, monkeypatch):
    (tmp_path / "module.py").write_text("secret content")

    def _forbidden_read(*args, **kwargs):
        raise AssertionError("RepositoryScanner must never read file contents")

    monkeypatch.setattr(Path, "read_bytes", _forbidden_read)
    monkeypatch.setattr(Path, "read_text", _forbidden_read)

    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()

    snapshot = scanner.scan(root)

    assert snapshot.results[0].relative_path.name == "module.py"


def test_scan_rejects_non_repository_root_argument(tmp_path):
    scanner = RepositoryScanner()

    with pytest.raises(TypeError):
        scanner.scan(tmp_path)


def test_repository_snapshot_is_immutable(tmp_path):
    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()
    snapshot = scanner.scan(root)

    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.results = ()


def test_scan_result_is_immutable(tmp_path):
    (tmp_path / "module.py").write_text("x")
    root = RepositoryRoot(path=tmp_path)
    scanner = RepositoryScanner()
    snapshot = scanner.scan(root)

    with pytest.raises(dataclasses.FrozenInstanceError):
        snapshot.results[0].size_bytes = 0
