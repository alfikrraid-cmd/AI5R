from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.template_loader import TemplateLoader
from FACTORY.FOUNDATION.component_generator import ComponentGenerator
from FACTORY.FOUNDATION.package_generator import PackageGenerator


def test_package_generator_creates_multiple_files(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()

    (templates / "object.tpl").write_text("class {{ class_name }}: pass")
    (templates / "readme.tpl").write_text("# {{ package_name }}")

    loader = TemplateLoader(templates)
    component_generator = ComponentGenerator(loader)
    package_generator = PackageGenerator(component_generator)

    output_dir = tmp_path / "PACKAGE"

    generated = package_generator.generate(
        output_dir=output_dir,
        files={
            "sample.py": "object.tpl",
            "README.md": "readme.tpl",
        },
        context={
            "class_name": "Sample",
            "package_name": "Sample Package",
        },
    )

    assert len(generated) == 2
    assert (output_dir / "sample.py").exists()
    assert (output_dir / "README.md").exists()
    assert (output_dir / "sample.py").read_text() == "class Sample: pass"
    assert (output_dir / "README.md").read_text() == "# Sample Package"
