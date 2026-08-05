from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

DEFAULT_CHUNK_SIZE = 65536
HasherFactory = Callable[[], Any]


@dataclass(frozen=True)
class FileHashResult:
    file_path: str
    algorithm: str
    hash_value: str
    byte_count: int
    chunk_size: int


class FileHashService:
    def __init__(
        self,
        hasher_factory: HasherFactory = sha256,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        algorithm_name: str = "sha256",
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")

        self._hasher_factory = hasher_factory
        self._chunk_size = chunk_size
        self._algorithm_name = algorithm_name

    def hash_file(self, file_path: Path) -> FileHashResult:
        if not isinstance(file_path, Path):
            raise TypeError("file_path must be a pathlib.Path")
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not file_path.is_file():
            raise ValueError(f"Not a file: {file_path}")

        hasher = self._hasher_factory()
        byte_count = 0

        with file_path.open("rb") as stream:
            while chunk := stream.read(self._chunk_size):
                hasher.update(chunk)
                byte_count += len(chunk)

        return FileHashResult(
            file_path=str(file_path),
            algorithm=self._algorithm_name,
            hash_value=hasher.hexdigest(),
            byte_count=byte_count,
            chunk_size=self._chunk_size,
        )
