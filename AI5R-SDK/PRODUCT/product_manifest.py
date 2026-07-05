from dataclasses import dataclass, field
from typing import Any


@dataclass
class ProductManifest:

    product_code: str

    product_name: str

    version: str

    runtime: str

    entrypoint: str

    dependencies: list[str] = field(default_factory=list)

    capabilities: list[str] = field(default_factory=list)

    policies: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    object_type: str = "PRODUCT_MANIFEST"

    status: str = "READY"
