import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.work_order_gateway import WorkOrderGateway, WorkOrderGatewayConfig


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
    return WorkOrderGateway(
        WorkOrderGatewayConfig(base_url="https://example.test/webhook", timeout=5)
    )


def test_create_work_order_forwards_request_and_returns_canonical_payload():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Work order created successfully",
        "data": {"work_order_code": "WO-101", "description": "Bearing replacement"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.create_work_order(
            {"work_order_code": "WO-101", "description": "Bearing replacement"}
        )

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/work-order/create"
    assert request.get_method() == "POST"
    assert json.loads(request.data.decode("utf-8")) == {
        "work_order_code": "WO-101",
        "description": "Bearing replacement",
    }
    assert result == canonical_response


def test_get_work_order_forwards_query_parameter():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Work order detail found",
        "data": {"work_order_code": "WO-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.get_work_order("WO-101")

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/work-order/detail?work_order_code=WO-101"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_list_work_orders_forwards_request():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Work orders listed",
        "count": 2,
        "data": [{"work_order_code": "WO-101"}, {"work_order_code": "WO-102"}],
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.list_work_orders()

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/work-order/list"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_update_work_order_forwards_request_body():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Work order updated successfully",
        "data": {"work_order_code": "WO-101", "status": "IN_PROGRESS"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.update_work_order({"work_order_code": "WO-101", "status": "IN_PROGRESS"})

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/work-order/update"
    assert request.get_method() == "PUT"
    assert json.loads(request.data.decode("utf-8")) == {
        "work_order_code": "WO-101",
        "status": "IN_PROGRESS",
    }
    assert result == canonical_response


def test_delete_work_order_forwards_query_parameter():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Work order deleted successfully",
        "data": {"work_order_code": "WO-101"},
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.delete_work_order("WO-101")

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/work-order/delete?work_order_code=WO-101"
    assert request.get_method() == "DELETE"
    assert result == canonical_response


def test_gateway_propagates_canonical_error_payload_on_http_error():
    gateway = _gateway()
    error_payload = {"success": False, "message": "Work order not found", "data": None}

    http_error = urllib.error.HTTPError(
        url="https://example.test/webhook/ltsa/work-order/detail",
        code=404,
        msg="Not Found",
        hdrs=None,
        fp=None,
    )

    with patch.object(http_error, "read", return_value=json.dumps(error_payload).encode("utf-8")):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = gateway.get_work_order("UNKNOWN")

    assert result == error_payload


def test_gateway_propagates_connection_failure():
    gateway = _gateway()

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        try:
            gateway.list_work_orders()
        except urllib.error.URLError:
            pass
        else:
            raise AssertionError("Expected URLError to propagate")


def test_gateway_uses_env_base_url_when_no_config_given(monkeypatch):
    monkeypatch.setenv("AI5R_WORK_ORDER_GATEWAY_BASE_URL", "https://env.test/webhook")

    gateway = WorkOrderGateway()

    assert gateway.config.base_url == "https://env.test/webhook"
