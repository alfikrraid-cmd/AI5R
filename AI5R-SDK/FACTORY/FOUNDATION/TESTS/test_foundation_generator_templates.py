from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.foundation_generator import FoundationGenerator


def test_foundation_generator_creates_component_templates(tmp_path):
    generator = FoundationGenerator()

    generated = generator.generate(
        foundation_name="sample_foundation",
        output_dir=tmp_path / "SAMPLE_FOUNDATION",
    )

    assert len(generated) == 9

    assert (tmp_path / "SAMPLE_FOUNDATION" / "sample_foundation.py").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "sample_foundation_registry.py").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "sample_foundation_validator.py").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "sample_foundation_runtime.py").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "manifest.json").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "sample_foundation_station.py").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "TESTS" / "test_sample_foundation.py").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "SPECIFICATION.md").exists()
    assert (tmp_path / "SAMPLE_FOUNDATION" / "FREEZE.md").exists()


def test_foundation_generator_content_is_rendered(tmp_path):
    generator = FoundationGenerator()

    generator.generate(
        foundation_name="memory_foundation",
        output_dir=tmp_path / "MEMORY_FOUNDATION",
    )

    content = (tmp_path / "MEMORY_FOUNDATION" / "memory_foundation.py").read_text()

    assert "class MemoryFoundation" in content
    assert "{{" not in content
