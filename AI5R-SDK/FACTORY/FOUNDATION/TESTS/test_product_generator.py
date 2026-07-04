from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.template_loader import TemplateLoader
from FACTORY.FOUNDATION.component_generator import ComponentGenerator
from FACTORY.FOUNDATION.package_generator import PackageGenerator
from FACTORY.FOUNDATION.product_generator import ProductGenerator


def test_product_generator_creates_product_package(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()

    (templates / "product.tpl").write_text("class {{ class_name }}: pass")
    (templates / "manifest.tpl").write_text("PRODUCT={{ product_code }}")

    loader = TemplateLoader(templates)
    component_generator = ComponentGenerator(loader)
    package_generator = PackageGenerator(component_generator)
    product_generator = ProductGenerator(package_generator)

    result = product_generator.generate(
        manifest={
            "product_name": "LTSA Brain",
            "product_code": "LTSA-BRAIN",
        },
        output_root=tmp_path,
        files={
            "{{ module_name }}.py": "product.tpl",
            "product.manifest": "manifest.tpl",
        },
    )

    output_dir = tmp_path / "LTSA-BRAIN"

    assert result["status"] == "PRODUCT_GENERATED"
    assert result["product_code"] == "LTSA-BRAIN"
    assert output_dir.exists()
    assert (output_dir / "{{ module_name }}.py").exists()
    assert (output_dir / "product.manifest").exists()
