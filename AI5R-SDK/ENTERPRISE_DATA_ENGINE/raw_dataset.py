from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {key: _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class ReaderMetadata:
    reader_name: str
    source_type: str
    media_type: str | None = None
    encoding: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "attributes", _freeze(self.attributes))


@dataclass(frozen=True)
class RawDataset:
    data: Any
    metadata: ReaderMetadata

    def __post_init__(self) -> None:
        object.__setattr__(self, "data", _freeze(self.data))


__all__ = ["RawDataset", "ReaderMetadata"]
