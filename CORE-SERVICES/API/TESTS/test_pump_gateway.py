import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.pump_gateway import PumpGateway, PumpGatewayConfig


class FakeHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _gateway():
    return PumpGateway(
        PumpGatewayConfig(base_url="https://example.test/webhook", timeout=5)
    )


def test_create_pump_forwards_request_and_returns_canonical_payload():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Pump created successfully",
        "data": {"tag_number": "P-101", "area": "Unit 1"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.create_pump({"tag_number": "P-101", "area": "Unit 1"})

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/pumps/create"
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {"tag_number": "P-101", "area": "Unit 1"}
    assert result == canonical_response


def test_create_pump_forwards_name_criticality_unchanged():
    # WO-PUMP-002 (implements ADR-PUMP-001): the gateway itself needed no
    # code change, since create_pump already forwards whatever payload dict
    # it is given. This test proves that payload-agnostic behavior actually
    # covers the two new fields, rather than merely asserting it.
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Pump created successfully",
        "data": {"tag_number": "P-101", "name": "Boiler Feedwater Pump 1A"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.create_pump(
            {
                "tag_number": "P-101",
                "area": "Unit 1",
                "name": "Boiler Feedwater Pump 1A",
                "criticality": "HIGH",
            }
        )

    request = urlopen.call_args[0][0]
    assert json.loads(request.data.decode("utf-8")) == {
        "tag_number": "P-101",
        "area": "Unit 1",
        "name": "Boiler Feedwater Pump 1A",
        "criticality": "HIGH",
    }
    assert result == canonical_response


def test_get_pump_forwards_query_parameter():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Pump detail found",
        "data": {"tag_number": "P-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.get_pump("P-101")

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/pump/detail?tag_number=P-101"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_list_pumps_forwards_request():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Pumps listed",
        "count": 2,
        "data": [{"tag_number": "P-101"}, {"tag_number": "P-102"}],
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.list_pumps()

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/pump/list"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_update_pump_forwards_request_body():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Pump updated successfully",
        "data": {"tag_number": "P-101", "status": "ACTIVE"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.update_pump({"tag_number": "P-101", "status": "ACTIVE"})

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/pump/update"
    assert request.get_method() == "PUT"
    assert json.loads(request.data.decode("utf-8")) == {"tag_number": "P-101", "status": "ACTIVE"}
    assert result == canonical_response


def test_delete_pump_forwards_query_parameter():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Pump deleted successfully",
        "data": {"tag_number": "P-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.delete_pump("P-101")

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/pump/delete?tag_number=P-101"
    assert request.get_method() == "DELETE"
    assert result == canonical_response


def test_gateway_propagates_canonical_error_payload_on_http_error():
    gateway = _gateway()
    error_payload = {"success": False, "message": "Pump not found", "data": None}

    http_error = urllib.error.HTTPError(
        url="https://example.test/webhook/ltsa/pump/detail",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )

    with patch.object(http_error, "read", return_value=json.dumps(error_payload).encode("utf-8")):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = gateway.get_pump("UNKNOWN")

    assert result == error_payload


def test_gateway_propagates_connection_failure():
    gateway = _gateway()

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        try:
            gateway.list_pumps()
        except urllib.error.URLError:
            pass
        else:
            raise AssertionError("Expected URLError to propagate")


def test_gateway_uses_env_base_url_when_no_config_given(monkeypatch):
    monkeypatch.setenv("AI5R_PUMP_GATEWAY_BASE_URL", "https://env.test/webhook")

    gateway = PumpGateway()

    assert gateway.config.base_url == "https://env.test/webhook"
