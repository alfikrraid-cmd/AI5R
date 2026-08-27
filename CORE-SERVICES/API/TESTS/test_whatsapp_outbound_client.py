import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.whatsapp_outbound_client import OutboundResult, WhatsAppOutboundClient, WhatsAppOutboundConfig


class FakeHTTPResponse:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


def _client(**overrides):
    config = WhatsAppOutboundConfig(
        base_url="https://example.test",
        api_version="v99.0",
        phone_number_id="PHONE_ID",
        access_token="secret-token",
        timeout=5,
    )
    for key, value in overrides.items():
        setattr(config, key, value)
    return WhatsAppOutboundClient(config)


def test_send_text_success_posts_expected_graph_api_request():
    client = _client()

    with patch("urllib.request.urlopen", return_value=FakeHTTPResponse(200)) as urlopen:
        result = client.send_text("+15550000001", "Reading date belum ada. Gunakan hari ini?")

    request = urlopen.call_args[0][0]
    assert request.full_url == "https://example.test/v99.0/PHONE_ID/messages"
    assert request.get_method() == "POST"
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert json.loads(request.data.decode("utf-8")) == {
        "messaging_product": "whatsapp",
        "to": "+15550000001",
        "type": "text",
        "text": {"body": "Reading date belum ada. Gunakan hari ini?"},
    }
    assert result == OutboundResult(status="SUCCESS", http_status=200)


def test_send_text_skipped_when_not_configured():
    client = WhatsAppOutboundClient(WhatsAppOutboundConfig(phone_number_id=None, access_token=None))

    with patch("urllib.request.urlopen") as urlopen:
        result = client.send_text("+15550000001", "hello")

    urlopen.assert_not_called()
    assert result.status == "SKIPPED"


def test_send_text_provider_http_error_returns_failed():
    client = _client()
    http_error = urllib.error.HTTPError(
        url="https://example.test/v99.0/PHONE_ID/messages", code=401, msg="Unauthorized", hdrs=None, fp=None
    )

    with patch("urllib.request.urlopen", side_effect=http_error):
        result = client.send_text("+15550000001", "hello")

    assert result.status == "FAILED"
    assert result.http_status == 401


def test_send_text_provider_unreachable_returns_failed():
    client = _client()

    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("connection refused")):
        result = client.send_text("+15550000001", "hello")

    assert result.status == "FAILED"
    assert result.error == "PROVIDER_UNREACHABLE"


def test_send_text_timeout_returns_failed():
    client = _client()

    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        result = client.send_text("+15550000001", "hello")

    assert result.status == "FAILED"
    assert result.error == "PROVIDER_TIMEOUT"


def test_client_uses_env_config_when_no_config_given(monkeypatch):
    monkeypatch.setenv("WHATSAPP_CLOUD_API_TOKEN", "env-token")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "env-phone-id")
    monkeypatch.setenv("WHATSAPP_GRAPH_API_VERSION", "v20.0")

    client = WhatsAppOutboundClient()

    assert client.config.access_token == "env-token"
    assert client.config.phone_number_id == "env-phone-id"
    assert client.config.api_version == "v20.0"
