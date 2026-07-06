from dataclasses import dataclass, field


CANONICAL_PRODUCT_PIPELINE = [
    "Specification",
    "Factory",
    "Artifact",
    "Registry",
    "Runtime",
    "Operation",
    "Evolution",
]


@dataclass
class ProductSpecification:
    product_name: str
    version: str = "1.0"
    domains: list[str] = field(default_factory=list)
    interfaces: list[str] = field(default_factory=list)
    runtime: str = "Python"

    def build(self):
        if not self.product_name:
            raise ValueError("product_name is required")

        return {
            "product": self.product_name.upper().replace(" ", "_"),
            "version": self.version,
            "domains": self.domains,
            "interfaces": self.interfaces,
            "runtime": self.runtime,
            "canonical_pipeline": CANONICAL_PRODUCT_PIPELINE,
            "status": "SPECIFIED",
        }
