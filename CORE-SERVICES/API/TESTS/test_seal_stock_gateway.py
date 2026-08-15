import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.seal_stock_gateway import SealStockGateway, SealStockGatewayConfig


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
    return SealStockGateway(SealStockGatewayConfig(base_url="https://example.test/webhook", timeout=5))


def test_list_seal_stocks_forwards_request():
    gateway = _gateway()
    canonical_response = {
        "success": True,
        "message": "Seal stock list retrieved",
        "count": 1,
        "data": [{"seal_code": "SC-001", "quantity_on_hand": 4, "reorder_point": 2, "location": "Warehouse A"}],
    }

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(canonical_response)) as urlopen:
        result = gateway.list_seal_stocks()

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/webhook/ltsa/seal-stock/list"
    assert request.get_method() == "GET"
    assert result == canonical_response


def test_gateway_has_no_write_methods():
    gateway = _gateway()
    assert not hasattr(gateway, "create_seal_stock")
    assert not hasattr(gateway, "update_seal_stock")
    assert not hasattr(gateway, "delete_seal_stock")


def test_gateway_propagates_canonical_error_payload_on_http_error():
    gateway = _gateway()
    error_payload = {"success": False, "message": "Seal stock API unavailable", "data": None}

    http_error = urllib.error.HTTPError(
        url="https://example.test/webhook/ltsa/seal-stock/list",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )

    with patch.object(http_error, "read", return_value=json.dumps(error_payload).encode("utf-8")):
        with patch("urllib.request.urlopen", side_effect=http_error):
            result = gateway.list_seal_stocks()

    assert result == error_payload


def test_gateway_uses_env_base_url_when_no_config_given(monkeypatch):
    monkeypatch.setenv("AI5R_SEAL_STOCK_GATEWAY_BASE_URL", "https://env.test/webhook")

    gateway = SealStockGateway()

    assert gateway.config.base_url == "https://env.test/webhook"


def test_gateway_returns_an_honest_failure_on_connection_level_failure_instead_of_raising():
    # See test_seal_gateway.py's identical regression test for the full
    # root-cause rationale (proven production spare-parts 500).
    gateway = _gateway()
    connection_error = urllib.error.URLError("Name or service not known")

    with patch("urllib.request.urlopen", side_effect=connection_error):
        result = gateway.list_seal_stocks()

    assert result["success"] is False
    assert result["data"] == []
    assert "ltsa/seal-stock/list" in result["error"]
