from datetime import datetime, UTC
from pathlib import Path

from PRODUCT_ASSEMBLY import ProductAssembly
from PRODUCT_ENGINE import ProductSpecification


class ProductArtifact:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.assembly = ProductAssembly(root_path)

    def manufacture(self, specification: ProductSpecification):
        assembled = self.assembly.assemble(specification)

        artifact = {
            "artifact_type": "PRODUCT",
            "product": assembled["product"],
            "version": "1.0",
            "status": "MANUFACTURED",
            "manufactured_at": datetime.now(UTC).isoformat(),
            "assembly_units": assembled["assembly_units"],
        }

        artifact_path = (
            Path(assembled["product_path"]) /
            "product_artifact.json"
        )

        artifact_path.write_text(
            str(artifact),
            encoding="utf-8",
        )

        return {
            "status": "PRODUCT_MANUFACTURED",
            "artifact": artifact,
            "artifact_path": str(artifact_path),
        }
