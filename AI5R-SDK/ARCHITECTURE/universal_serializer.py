from __future__ import annotations

import json
from typing import Any, Type, TypeVar

T = TypeVar("T")


class UniversalSerializer:
    """
    AX-007 Universal Serialization Contract
    Shared serializer/deserializer for AI5R core records.
    """

    @staticmethod
    def to_dict(obj: Any) -> dict[str, Any]:
        if hasattr(obj, "to_dict"):
            return obj.to_dict()

        raise TypeError(f"Object {type(obj).__name__} does not support to_dict()")

    @staticmethod
    def to_json(obj: Any) -> str:
        return json.dumps(
            UniversalSerializer.to_dict(obj),
            sort_keys=True,
            ensure_ascii=False,
        )

    @staticmethod
    def from_dict(cls: Type[T], data: dict[str, Any]) -> T:
        return cls(**data)

    @staticmethod
    def from_json(cls: Type[T], payload: str) -> T:
        data = json.loads(payload)
        return UniversalSerializer.from_dict(cls, data)
