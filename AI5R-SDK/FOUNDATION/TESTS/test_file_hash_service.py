import hashlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from FOUNDATION.file_hash_service import DEFAULT_CHUNK_SIZE, FileHashResult, FileHashService


@pytest.fixture
def small_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "small.txt"
    file_path.write_bytes(b"AI5R Foundation FileHashService")
    return file_path


@pytest.fixture
def large_file(tmp_path: Path) -> Path:
    file_path = tmp_path / "large.bin"
    file_path.write_bytes(b"\x00\x01\x02\x03" * 100_000)
    return file_path


def test_hash_file_returns_correct_sha256_digest(small_file: Path):
    service = FileHashService()

    result = service.hash_file(small_file)

    expected = hashlib.sha256(small_file.read_bytes()).hexdigest()
    assert result.hash_value == expected


def test_hash_file_returns_file_hash_result(small_file: Path):
    service = FileHashService()

    result = service.hash_file(small_file)

    assert isinstance(result, FileHashResult)
    assert result.file_path == str(small_file)
    assert result.algorithm == "sha256"
    assert result.byte_count == small_file.stat().st_size


def test_hash_file_matches_reference_digest_for_large_file(large_file: Path):
    service = FileHashService(chunk_size=4096)

    result = service.hash_file(large_file)

    expected = hashlib.sha256(large_file.read_bytes()).hexdigest()
    assert result.hash_value == expected
    assert result.byte_count == large_file.stat().st_size


def test_hash_file_uses_incremental_chunked_reads_not_read_bytes(large_file: Path, monkeypatch):
    service = FileHashService(chunk_size=1024)

    def _forbidden_read_bytes(self):
        raise AssertionError("read_bytes() must not be used for chunked hashing")

    monkeypatch.setattr(Path, "read_bytes", _forbidden_read_bytes)

    result = service.hash_file(large_file)

    assert result.byte_count == len(b"\x00\x01\x02\x03" * 100_000)


def test_hash_file_default_chunk_size_is_used_when_not_injected(small_file: Path):
    service = FileHashService()

    result = service.hash_file(small_file)

    assert result.chunk_size == DEFAULT_CHUNK_SIZE


def test_hash_file_respects_injected_chunk_size(small_file: Path):
    service = FileHashService(chunk_size=8)

    result = service.hash_file(small_file)

    assert result.chunk_size == 8


def test_hash_file_respects_injected_hasher_factory(small_file: Path):
    calls: list[str] = []

    def tracking_hasher_factory():
        calls.append("created")
        return hashlib.sha256()

    service = FileHashService(hasher_factory=tracking_hasher_factory)

    service.hash_file(small_file)

    assert calls == ["created"]


def test_hash_file_raises_file_not_found_for_missing_file(tmp_path: Path):
    service = FileHashService()
    missing = tmp_path / "does-not-exist.txt"

    with pytest.raises(FileNotFoundError):
        service.hash_file(missing)


def test_hash_file_raises_value_error_for_directory(tmp_path: Path):
    service = FileHashService()

    with pytest.raises(ValueError):
        service.hash_file(tmp_path)


def test_hash_file_raises_type_error_for_non_path_argument():
    service = FileHashService()

    with pytest.raises(TypeError):
        service.hash_file("not-a-path-object")


def test_constructor_rejects_zero_chunk_size():
    with pytest.raises(ValueError):
        FileHashService(chunk_size=0)


def test_constructor_rejects_negative_chunk_size():
    with pytest.raises(ValueError):
        FileHashService(chunk_size=-1)


def test_hash_file_empty_file_matches_known_sha256_empty_digest(tmp_path: Path):
    empty_file = tmp_path / "empty.txt"
    empty_file.write_bytes(b"")
    service = FileHashService()

    result = service.hash_file(empty_file)

    assert result.hash_value == hashlib.sha256(b"").hexdigest()
    assert result.byte_count == 0


def test_file_hash_result_is_immutable(small_file: Path):
    service = FileHashService()
    result = service.hash_file(small_file)

    with pytest.raises(Exception):
        result.hash_value = "tampered"
