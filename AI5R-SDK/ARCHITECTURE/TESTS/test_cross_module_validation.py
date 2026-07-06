from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.VALIDATION import CrossModuleValidator


def test_cross_module_validation():
    validator = CrossModuleValidator()

    result = validator.validate_imports()

    assert result.success is True
    assert len(result.scanned_modules) > 10
    assert result.import_failures == []
