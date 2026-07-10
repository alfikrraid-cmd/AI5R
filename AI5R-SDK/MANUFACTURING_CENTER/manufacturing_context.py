from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True, kw_only=True)
class ManufacturingContext:
    manufacturing_id: str
    mwo: dict[str, Any]
    product_name: str
    factory: str
    runtime: str
    workspace: Path
    variables: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.manufacturing_id = self.manufacturing_id.strip()
        self.product_name = self.product_name.strip()
        self.factory = self.factory.strip()
        self.runtime = self.runtime.strip()

        if not self.manufacturing_id:
            raise ValueError("manufacturing_id must not be empty")
        if not self.mwo:
            raise ValueError("mwo must not be empty")
        if not self.product_name:
            raise ValueError("product_name must not be empty")
        if not self.factory:
            raise ValueError("factory must not be empty")
        if not self.runtime:
            raise ValueError("runtime must not be empty")
        if not isinstance(self.workspace, Path):
            raise TypeError("workspace must be a Path")
        if not self.workspace.is_absolute():
            raise ValueError("workspace must be an absolute path")

        self.mwo = dict(self.mwo)
        self.variables = dict(self.variables)
        self.metadata = dict(self.metadata)

    @staticmethod
    def _clean_key(name: str, *, field_name: str) -> str:
        cleaned_name = name.strip()
        if not cleaned_name:
            raise ValueError(f"{field_name} must not be empty")
        return cleaned_name

    def set_variable(self, name: str, value: Any) -> None:
        cleaned_name = self._clean_key(
            name,
            field_name="variable name",
        )
        self.variables[cleaned_name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        cleaned_name = self._clean_key(
            name,
            field_name="variable name",
        )
        return self.variables.get(cleaned_name, default)

    def update_metadata(self, values: dict[str, Any]) -> None:
        cleaned_values: dict[str, Any] = {}

        for key, value in values.items():
            if not isinstance(key, str):
                raise TypeError("metadata key must be a string")

            cleaned_key = self._clean_key(
                key,
                field_name="metadata key",
            )
            cleaned_values[cleaned_key] = value

        self.metadata.update(cleaned_values)

    @property
    def workspace_exists(self) -> bool:
        return self.workspace.exists()
