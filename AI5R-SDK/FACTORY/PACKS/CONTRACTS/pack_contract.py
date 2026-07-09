from dataclasses import dataclass, field


@dataclass
class FactoryPackContract:

    pack_id: str

    pack_name: str

    version: str

    product_type: str

    blueprint: str

    recipe: str

    templates_path: str

    validation_module: str

    manifest_path: str

    metadata: dict = field(default_factory=dict)


REQUIRED_FIELDS = (
    "pack_id",
    "pack_name",
    "version",
    "product_type",
    "blueprint",
    "recipe",
    "templates_path",
    "validation_module",
    "manifest_path",
)
