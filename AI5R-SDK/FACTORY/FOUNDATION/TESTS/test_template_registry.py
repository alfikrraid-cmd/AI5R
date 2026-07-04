from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.template_registry import TemplateRegistry


def test_template_registry_returns_standard_templates():
    registry = TemplateRegistry()

    templates = registry.get("standard")

    assert "{{module_name}}.py" in templates
    assert "{{module_name}}_registry.py" in templates
    assert "{{module_name}}_validator.py" in templates
    assert "SPECIFICATION.md" in templates
    assert "FREEZE.md" in templates


def test_template_registry_returns_legacy_templates():
    registry = TemplateRegistry()

    templates = registry.get("legacy")

    assert "__init__.py" in templates
    assert "{{module_name}}_object.py" in templates
    assert "{{module_name}}_validation_engine.py" in templates
    assert "DOCS/{{foundation_code}}-SPECIFICATION.md" in templates
    assert "DOCS/{{foundation_upper}}-FOUNDATION-FREEZE-v1.0.md" in templates


def test_template_registry_rejects_unknown_mode():
    registry = TemplateRegistry()

    try:
        registry.get("unknown")
        assert False
    except ValueError as error:
        assert "Unknown template mode" in str(error)
