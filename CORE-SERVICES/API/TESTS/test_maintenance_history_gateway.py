import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.maintenance_history_gateway import (
    MaintenanceHistoryGateway,
    MaintenanceHistoryGatewayConfig,
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


def _gateway():
    return MaintenanceHistoryGateway(
        MaintenanceHistoryGatewayConfig(base_url="https://example.test/webhook", timeout=5)
    )


def test_create_maintenance_history_forwards_request_and_returns_canonical_payload():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Maintenance history record created successfully",
        "data": {"maintenance_record_code": "MH-101", "work_order_code": "WO-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.create_maintenance_history(
            {"maintenance_record_code": "MH-101", "work_order_code": "WO-101"}
        )

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/maintenance-history/create"
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {
        "maintenance_record_code": "MH-101",
        "work_order_code": "WO-101",
    }
    assert result == canonical_response


def test_get_maintenance_history_forwards_query_parameter():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Maintenance history detail found",
        "data": {"maintenance_record_code": "MH-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.get_maintenance_history("MH-101")

    request = urlopen.call_args[0][0]
    assert (
        request.full_url
        == "https://example.test/webhook/ltsa/maintenance-history/detail?maintenance_record_code=MH-101"
    )
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_list_maintenance_history_forwards_request():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Maintenance history listed",
        "count": 2,
        "data": [{"maintenance_record_code": "MH-101"}, {"maintenance_record_code": "MH-102"}],
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.list_maintenance_history()

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/maintenance-history/list"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_update_maintenance_history_forwards_request_body():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Maintenance history updated successfully",
        "data": {"maintenance_record_code": "MH-101", "status": "CLOSED"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.update_maintenance_history(
            {"maintenance_record_code": "MH-101", "status": "CLOSED"}
        )

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/maintenance-history/update"
    assert request.get_method() == "PUT"
    assert json.loads(request.data.decode("utf-8")) == {
        "maintenance_record_code": "MH-101",
        "status": "CLOSED",
    }
    assert result == canonical_response


def test_delete_maintenance_history_forwards_query_parameter():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Maintenance history deleted successfully",
        "data": {"maintenance_record_code": "MH-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.delete_maintenance_history("MH-101")

    request = urlopen.call_args[0][0]
    assert (
        request.full_url
        == "https://example.test/webhook/ltsa/maintenance-history/delete?maintenance_record_code=MH-101"
    )
    assert request.get_method() == "DELETE"
    assert result == canonical_response


def test_gateway_propagates_canonical_error_payload_on_http_error():
    gateway = _gateway()
    error_payload = {"success": False, "message": "Maintenance history record not found", "data": None}

    http_error = urllib.error.HTTPError(
        url="https://example.test/webhook/ltsa/maintenance-history/detail",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )

    with patch.object(http_error, "read", return_value=json.dumps(error_payload).encode("utf-8")):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = gateway.get_maintenance_history("UNKNOWN")

    assert result == error_payload


def test_gateway_propagates_connection_failure():
    gateway = _gateway()

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        try:
            gateway.list_maintenance_history()
        except urllib.error.URLError:
            pass
        else:
            raise AssertionError("Expected URLError to propagate")


def test_gateway_uses_env_base_url_when_no_config_given(monkeypatch):
    monkeypatch.setenv("AI5R_MAINTENANCE_HISTORY_GATEWAY_BASE_URL", "https://env.test/webhook")

    gateway = MaintenanceHistoryGateway()

    assert gateway.config.base_url == "https://env.test/webhook"
