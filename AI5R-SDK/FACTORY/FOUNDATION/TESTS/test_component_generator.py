from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.template_loader import TemplateLoader
from FACTORY.FOUNDATION.component_generator import ComponentGenerator


def test_component_generator_creates_file(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()

    (templates / "hello.tpl").write_text("Hello {{ name }}")

    loader = TemplateLoader(templates)
    generator = ComponentGenerator(loader)

    output = tmp_path / "hello.txt"

    result = generator.generate(
        template_name="hello.tpl",
        destination=output,
        context={"name": "AI5R"},
    )

    assert result == str(output)
    assert output.exists()
    assert output.read_text() == "Hello AI5R"
