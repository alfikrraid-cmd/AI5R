import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.seal_pump_compatibility_gateway import (
    SealPumpCompatibilityGateway,
    SealPumpCompatibilityGatewayConfig,
)


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


class FakeEmptyHTTPResponse:
    """See test_seal_gateway.py's identical fake for the full rationale:
    reproduces HTTP 200 + empty body, exactly what n8n sent for a
    zero-row query before the canonical workflow fix."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return b""


def _gateway():
    return SealPumpCompatibilityGateway(
        SealPumpCompatibilityGatewayConfig(base_url="https://example.test/webhook", timeout=5)
    )


def test_list_seal_pump_compatibilities_forwards_request():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Seal-Pump compatibility list retrieved",
        "count": 1,
        "data": [{"seal_code": "SC-001", "pump_tag_number": "641-P-5"}],
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.list_seal_pump_compatibilities()

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/seal-pump-compatibility/list"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_gateway_has_no_write_methods():
    gateway = _gateway()
    assert not hasattr(gateway, "create_seal_pump_compatibility")
    assert not hasattr(gateway, "update_seal_pump_compatibility")
    assert not hasattr(gateway, "delete_seal_pump_compatibility")


def test_gateway_propagates_canonical_error_payload_on_http_error():
    gateway = _gateway()
    error_payload = {"success": False, "message": "Seal-Pump compatibility API unavailable", "data": None}

    http_error = urllib.error.HTTPError(
        url="https://example.test/webhook/ltsa/seal-pump-compatibility/list",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    with patch.object(http_error, "read", return_value=json.dumps(error_payload).encode("utf-8")):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = gateway.list_seal_pump_compatibilities()

    assert result == error_payload


def test_gateway_uses_env_base_url_when_no_config_given(monkeypatch):
    monkeypatch.setenv("AI5R_SEAL_PUMP_COMPATIBILITY_GATEWAY_BASE_URL", "https://env.test/webhook")

    gateway = SealPumpCompatibilityGateway()

    assert gateway.config.base_url == "https://env.test/webhook"


def test_gateway_returns_an_honest_failure_on_connection_level_failure_instead_of_raising():
    # See test_seal_gateway.py's identical regression test for the full
    # root-cause rationale (proven production spare-parts 500).
    gateway = _gateway()
    connection_error = urllib.error.URLError("Name or service not known")

    with patch("urllib.request.urlopen", side_effect=connection_error):
        result = gateway.list_seal_pump_compatibilities()

    assert result["success"] is False
    assert result["data"] == []
    assert "ltsa/seal-pump-compatibility/list" in result["error"]


def test_gateway_returns_an_honest_failure_on_an_empty_body_instead_of_raising_jsondecodeerror():
    # Scenario G (MWO-LTSA-PROD-ZERO-ROW-001): see test_seal_gateway.py's
    # identical regression test for the full rationale.
    gateway = _gateway()

    with patch("urllib.request.urlopen", return_value=FakeEmptyHTTPResponse()):
        result = gateway.list_seal_pump_compatibilities()

    assert result["success"] is False
    assert result["data"] == []
    assert "ltsa/seal-pump-compatibility/list" in result["error"]
