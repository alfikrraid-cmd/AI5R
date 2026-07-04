from pathlib import Path

try:
    from .package_generator import PackageGenerator
except ImportError:
    from package_generator import PackageGenerator


class ProductGenerator:
    """
    Generates a product package from a product manifest.
    """

    def __init__(self, package_generator: PackageGenerator):
        self.package_generator = package_generator

    def generate(self, manifest: dict, output_root: str | Path, files: dict) -> dict:
        product_name = manifest["product_name"]
        product_code = manifest["product_code"]

        output_dir = Path(output_root) / product_code

        context = {
            "product_name": product_name,
            "product_code": product_code,
            "class_name": self._to_class_name(product_name),
            "module_name": self._to_module_name(product_name),
        }

        generated = self.package_generator.generate(
            output_dir=output_dir,
            files=files,
            context=context,
        )

        return {
            "status": "PRODUCT_GENERATED",
            "product_name": product_name,
            "product_code": product_code,
            "output_dir": str(output_dir),
            "generated_files": generated,
        }

    def _to_class_name(self, value: str) -> str:
        return "".join(part.capitalize() for part in value.replace("-", "_").replace(" ", "_").split("_"))

    def _to_module_name(self, value: str) -> str:
        return value.replace("-", "_").replace(" ", "_").lower()
