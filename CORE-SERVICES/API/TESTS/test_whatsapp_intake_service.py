"""MWO-LTSA-WHATSAPP-PHONE-CANONICALIZATION-001 -- normalize_sender_identifier/
hash_sender_identifier canonicalization tests. Pure-function tests, no DB.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.whatsapp_intake_service import hash_sender_identifier, normalize_sender_identifier  # noqa: E402


class TestIndonesianEquivalence:
    @pytest.mark.parametrize(
        "raw",
        [
            "081234567890",
            "6281234567890",
            "+6281234567890",
            "0812-3456-7890",
            "0812 3456 7890",
            "+62 812 3456 7890",
            "62-812-3456-7890",
        ],
    )
    def test_all_representations_normalize_to_canonical_e164(self, raw):
        assert normalize_sender_identifier(raw) == "+6281234567890"

    def test_all_representations_produce_identical_sender_hash(self):
        representations = [
            "081234567890",
            "6281234567890",
            "+6281234567890",
            "0812-3456-7890",
            "0812 3456 7890",
        ]
        hashes = {hash_sender_identifier(normalize_sender_identifier(r)) for r in representations}
        assert len(hashes) == 1


class TestNonIndonesianAndEdgeCases:
    def test_international_e164_number_is_preserved(self):
        assert normalize_sender_identifier("+15550000001") == "+15550000001"

    def test_international_number_without_leading_zero_untouched(self):
        assert normalize_sender_identifier("15550000001") == "+15550000001"

    def test_zero_prefixed_non_mobile_number_is_not_rewritten_to_62(self):
        # Not an Indonesian mobile shape (0 + 8...) -- left as its own
        # (still valid-length) digit string, never guessed at.
        assert normalize_sender_identifier("0215550001") == "+0215550001"

    def test_invalid_short_number_raises(self):
        with pytest.raises(ValueError):
            normalize_sender_identifier("08123")

    def test_invalid_characters_only_raises(self):
        with pytest.raises(ValueError):
            normalize_sender_identifier("abc-def")

    def test_empty_value_raises(self):
        with pytest.raises(ValueError):
            normalize_sender_identifier("")

    def test_too_long_number_raises(self):
        with pytest.raises(ValueError):
            normalize_sender_identifier("+1234567890123456")
