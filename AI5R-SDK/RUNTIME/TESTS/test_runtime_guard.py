from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from RUNTIME.HARDENING import RuntimeGuard


def test_guard_clean_code():
    guard = RuntimeGuard()

    result = guard.validate_code(
        "MODULE_A",
        "print('hello')",
    )

    assert result.is_clean is True


def test_guard_forbidden():
    guard = RuntimeGuard()

    result = guard.validate_code(
        "MODULE_A",
        "exec('print(1)')",
    )

    assert result.is_clean is False


def test_contract_validation():
    guard = RuntimeGuard()

    result = guard.validate_contracts(
        {
            "A": 1,
            "B": None,
        }
    )

    assert result.is_clean is False
