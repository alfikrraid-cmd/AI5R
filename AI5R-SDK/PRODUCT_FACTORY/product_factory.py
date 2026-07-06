from pathlib import Path

from PRODUCT_ENGINE import ProductSpecification
from DOMAIN_GENERATOR import AI5RDomainGenerator
from DOMAIN_VALIDATOR import AI5RDomainValidator


class ProductFactory:
    def __init__(self, root_path):
        self.root_path = Path(root_path)
        self.domain_generator = AI5RDomainGenerator(self.root_path)
        self.domain_validator = AI5RDomainValidator(self.root_path)

    def build(self, specification: ProductSpecification):
        product_spec = specification.build()

        product_name = product_spec["product"]
        product_path = self.root_path / "PRODUCTS" / product_name
        product_path.mkdir(parents=True, exist_ok=True)

        generated_domains = []

        for domain in product_spec["domains"]:
            generated = self.domain_generator.generate(domain)
            validation = self.domain_validator.validate(domain)

            generated_domains.append({
                "domain": generated["domain_name"],
                "status": validation["status"],
                "score": validation["score"],
            })

        manifest_path = product_path / "product_manifest.py"
        manifest_path.write_text(
            f'''PRODUCT_NAME = "{product_name}"
PRODUCT_VERSION = "{product_spec["version"]}"
PRODUCT_RUNTIME = "{product_spec["runtime"]}"

DOMAINS = {generated_domains}

CANONICAL_PIPELINE = {product_spec["canonical_pipeline"]}
''',
            encoding="utf-8",
        )

        return {
            "status": "PRODUCT_BUILT",
            "product": product_name,
            "version": product_spec["version"],
            "product_path": str(product_path),
            "domains": generated_domains,
            "manifest": str(manifest_path),
        }
