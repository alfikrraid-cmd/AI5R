import json
import subprocess
import sys
from pathlib import Path

_MODULE_DIR = Path(__file__).resolve().parents[1]
_CLI = _MODULE_DIR / "resolve_identity_cli.py"


def _run(object_type: str, payload: dict) -> dict:
    result = subprocess.run(
        [sys.executable, str(_CLI), "--object-type", object_type],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_resolves_matching_pump_by_tag_number():
    output = _run(
        "PUMP",
        {
            "candidate_key": {"tag_number": "P-101"},
            "known": [{"id": "uuid-1", "tag_number": "P-101"}],
        },
    )
    assert output == {"matched": True, "canonical_id": "uuid-1", "confidence": 1.0}


def test_no_match_when_tag_number_absent():
    output = _run(
        "PUMP",
        {"candidate_key": {"tag_number": "P-999"}, "known": [{"id": "uuid-1", "tag_number": "P-101"}]},
    )
    assert output == {"matched": False, "canonical_id": None, "confidence": None}


def test_resolves_matching_seal_by_seal_code():
    output = _run(
        "SEAL",
        {
            "candidate_key": {"seal_code": "JC-100"},
            "known": [{"seal_code": "JC-100"}],
        },
    )
    assert output == {"matched": True, "canonical_id": "JC-100", "confidence": 1.0}
