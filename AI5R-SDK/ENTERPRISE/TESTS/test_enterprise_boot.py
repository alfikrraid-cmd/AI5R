from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ENTERPRISE import EnterpriseBoot


def test_enterprise_boot():
    boot = EnterpriseBoot()

    result = boot.full_boot()

    assert result.success is True
    assert "kernel" in result.boot_steps
    assert "brain" in result.boot_steps
    assert "shutdown" in result.boot_steps
