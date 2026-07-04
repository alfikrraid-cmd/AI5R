from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.template_loader import TemplateLoader


def test_template_loader_renders_context(tmp_path):
    template_dir = tmp_path / "templates"
    template_dir.mkdir()

    template = template_dir / "sample.tpl"
    template.write_text("Hello {{ name }}")

    loader = TemplateLoader(template_dir)

    result = loader.render("sample.tpl", {"name": "AI5R"})

    assert result == "Hello AI5R"
