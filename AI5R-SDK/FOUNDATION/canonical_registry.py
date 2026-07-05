from dataclasses import dataclass
from typing import Any


@dataclass
class RegistryEntry:
    key: str
    target: Any
    metadata: dict[str, Any]


class CanonicalRegistry:
    def __init__(self):
        self._entries: dict[str, RegistryEntry] = {}

    def register(
        self,
        key: str,
        target: Any,
        metadata: dict[str, Any] | None = None,
    ) -> RegistryEntry:
        if not key:
            raise ValueError("registry key is required")
        if target is None:
            raise ValueError("registry target is required")

        normalized_key = key.upper()

        entry = RegistryEntry(
            key=normalized_key,
            target=target,
            metadata=metadata or {},
        )

        self._entries[normalized_key] = entry
        return entry

    def resolve(self, key: str) -> Any:
        if not key:
            raise ValueError("registry key is required")

        normalized_key = key.upper()

        if normalized_key not in self._entries:
            raise KeyError(f"Registry key not found: {normalized_key}")

        return self._entries[normalized_key].target

    def get_entry(self, key: str) -> RegistryEntry:
        if not key:
            raise ValueError("registry key is required")

        normalized_key = key.upper()

        if normalized_key not in self._entries:
            raise KeyError(f"Registry key not found: {normalized_key}")

        return self._entries[normalized_key]

    def contains(self, key: str) -> bool:
        return key.upper() in self._entries

    def unregister(self, key: str) -> None:
        if not key:
            raise ValueError("registry key is required")

        normalized_key = key.upper()

        if normalized_key in self._entries:
            del self._entries[normalized_key]

    def keys(self) -> list[str]:
        return list(self._entries.keys())

    def entries(self) -> list[RegistryEntry]:
        return list(self._entries.values())

    def clear(self) -> None:
        self._entries.clear()
