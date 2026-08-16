import sys
from pathlib import Path

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_password import hash_password, verify_password  # noqa: E402


def test_hash_password_is_never_the_raw_password():
    encoded = hash_password("correct horse battery staple")
    assert "correct horse battery staple" not in encoded
    assert encoded.startswith("scrypt$")


def test_verify_password_accepts_the_correct_password():
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded) is True


def test_verify_password_rejects_the_wrong_password():
    encoded = hash_password("correct horse battery staple")
    assert verify_password("wrong password", encoded) is False


def test_two_hashes_of_the_same_password_are_never_identical_real_salting():
    first = hash_password("same password")
    second = hash_password("same password")
    assert first != second
    assert verify_password("same password", first) is True
    assert verify_password("same password", second) is True


def test_verify_password_never_raises_on_a_malformed_encoded_hash():
    assert verify_password("anything", "not-a-real-hash") is False
    assert verify_password("anything", "") is False
    assert verify_password("anything", "scrypt$notanumber$8$1$AA==$AA==") is False


def test_hash_password_rejects_an_empty_password():
    import pytest

    with pytest.raises(ValueError):
        hash_password("")
