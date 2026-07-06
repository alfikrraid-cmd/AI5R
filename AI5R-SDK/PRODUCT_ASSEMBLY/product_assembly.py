from pathlib import Path

from PRODUCT_FACTORY import ProductFactory
from PRODUCT_ENGINE import ProductSpecification


class ProductAssembly:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.factory = ProductFactory(self.root_path)

    def assemble(self, specification: ProductSpecification):
        built_product = self.factory.build(specification)

        product_name = built_product["product"]
        product_path = self.root_path / "PRODUCTS" / product_name
        assembly_path = product_path / "assembly_manifest.py"

        domains = built_product["domains"]

        assembly_units = []

        for domain in domains:
            assembly_units.append({
                "domain": domain["domain"],
                "status": "ASSEMBLED",
                "source_status": domain["status"],
            })

        assembly_path.write_text(
            f'''PRODUCT_NAME = "{product_name}"
ASSEMBLY_STATUS = "ASSEMBLED"

ASSEMBLY_UNITS = {assembly_units}
''',
            encoding="utf-8",
        )

        return {
            "status": "PRODUCT_ASSEMBLED",
            "product": product_name,
            "product_path": str(product_path),
            "assembly_manifest": str(assembly_path),
            "assembly_units": assembly_units,
        }
