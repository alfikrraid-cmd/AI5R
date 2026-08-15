import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.seal_gateway import SealGateway, SealGatewayConfig


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
    """Reproduces the exact production defect: HTTP 200, Content-Type
    application/json, but a completely empty body -- what n8n 1.115.3
    actually sent whenever the Postgres node behind this webhook
    returned zero rows and alwaysOutputData was unset (root cause,
    proven and fixed in the canonical workflow JSON itself)."""

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return b""


def _gateway():
    return SealGateway(SealGatewayConfig(base_url="https://example.test/webhook", timeout=5))


def test_list_seals_forwards_request():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Seal list retrieved",
        "count": 1,
        "data": [{"seal_code": "SC-001", "seal_name": "John Crane Type 21"}],
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.list_seals()

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/seal/list"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_gateway_has_no_write_methods():
    # Disclosed judgment call: Inventory Context (MWO-INV-CTX-001) is
    # read-only engineering context, not an Inventory Module -- this test
    # proves the gateway surface actually reflects that scope rather than
    # silently growing write methods later without a matching MWO.
    gateway = _gateway()
    assert not hasattr(gateway, "create_seal")
    assert not hasattr(gateway, "update_seal")
    assert not hasattr(gateway, "delete_seal")


def test_gateway_propagates_canonical_error_payload_on_http_error():
    gateway = _gateway()
    error_payload = {"success": False, "message": "Seal API unavailable", "data": None}

    http_error = urllib.error.HTTPError(
        url="https://example.test/webhook/ltsa/seal/list",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    with patch.object(http_error, "read", return_value=json.dumps(error_payload).encode("utf-8")):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = gateway.list_seals()

    assert result == error_payload


def test_gateway_uses_env_base_url_when_no_config_given(monkeypatch):
    monkeypatch.setenv("AI5R_SEAL_GATEWAY_BASE_URL", "https://env.test/webhook")

    gateway = SealGateway()

    assert gateway.config.base_url == "https://env.test/webhook"


def test_gateway_returns_an_honest_failure_on_connection_level_failure_instead_of_raising():
    # Regression: production evidence showed spare-parts endpoints (which
    # call this gateway) returning a bare HTTP 500. Root cause, proven
    # against a real container: urllib.error.URLError (connection
    # refused/DNS failure/timeout -- HTTPError's own parent class, not a
    # subclass of it) was never caught here, so it propagated uncaught
    # all the way to FastAPI's default 500 handler. This asserts the
    # gateway itself never raises for this case.
    gateway = _gateway()
    connection_error = urllib.error.URLError("Name or service not known")

    with patch("urllib.request.urlopen", side_effect=connection_error):
        result = gateway.list_seals()

    assert result["success"] is False
    assert result["data"] == []
    assert "ltsa/seal/list" in result["error"]


def test_gateway_returns_an_honest_failure_on_an_empty_body_instead_of_raising_jsondecodeerror():
    # Scenario G (MWO-LTSA-PROD-ZERO-ROW-001): secondary defense only --
    # the canonical workflow fix (alwaysOutputData) is what actually
    # prevents this response from occurring; this proves that IF a
    # malformed/empty response ever reaches this gateway regardless, it
    # degrades to an honest success=False result instead of letting
    # json.JSONDecodeError propagate uncaught into a bare 500. The empty
    # body is never silently reinterpreted as a legitimate "[]" result --
    # success stays False, with a real diagnostic message.
    gateway = _gateway()

    with patch("urllib.request.urlopen", return_value=FakeEmptyHTTPResponse()):
        result = gateway.list_seals()

    assert result["success"] is False
    assert result["data"] == []
    assert "ltsa/seal/list" in result["error"]
