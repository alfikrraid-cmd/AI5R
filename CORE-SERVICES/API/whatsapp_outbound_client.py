from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

DEFAULT_GRAPH_API_BASE_URL = "https://graph.facebook.com"
DEFAULT_GRAPH_API_VERSION = "v23.0"


@dataclass(frozen=True, slots=True)
class OutboundResult:
    status: str  # "SUCCESS" | "FAILED" | "SKIPPED"
    http_status: int | None = None
    error: str | None = None
    provider_message_id: str | None = None


@dataclass(slots=True)
class WhatsAppOutboundConfig:
    base_url: str = DEFAULT_GRAPH_API_BASE_URL
    api_version: str = DEFAULT_GRAPH_API_VERSION
    phone_number_id: str | None = None
    access_token: str | None = None
    timeout: int = 10


class WhatsAppOutboundClient:
    """Transport layer only: sends a single WhatsApp Cloud API text message.

    No reply-text construction and no intake/business logic here -- callers
    (whatsapp_webhook.py) supply the already-decided reply from
    whatsapp_intake_service.IntakeResult.reply. Same env var names already
    established by CORE-SERVICES/RUNTIME/WORKFLOWS/
    WF-LTSA-WHATSAPP-INTAKE-024A.json's "Send WhatsApp Reply" node (that
    artifact was never wired into the live inbound path -- confirmed by
    reading nginx/n8n logs -- so this is the first live implementation of
    that config contract, not a second one).
    """

    def __init__(self, config: WhatsAppOutboundConfig | None = None):
        self.config = config or WhatsAppOutboundConfig(
            base_url=os.getenv("WHATSAPP_GRAPH_API_BASE_URL", DEFAULT_GRAPH_API_BASE_URL),
            api_version=os.getenv("WHATSAPP_GRAPH_API_VERSION", DEFAULT_GRAPH_API_VERSION),
            phone_number_id=os.getenv("WHATSAPP_PHONE_NUMBER_ID"),
            access_token=os.getenv("WHATSAPP_CLOUD_API_TOKEN"),
            timeout=int(os.getenv("WHATSAPP_OUTBOUND_TIMEOUT_SECONDS", "10")),
        )

    def send_text(self, recipient: str, text: str) -> OutboundResult:
        if not self.config.phone_number_id or not self.config.access_token:
            return OutboundResult(status="SKIPPED", error="OUTBOUND_NOT_CONFIGURED")

        url = f"{self.config.base_url.rstrip('/')}/{self.config.api_version}/{self.config.phone_number_id}/messages"
        body = json.dumps(
            {
                "messaging_product": "whatsapp",
                "to": recipient,
                "type": "text",
                "text": {"body": text},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.access_token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                # MWO-025J2 -- capture Meta's own assigned id for this
                # outbound message so a later inbound reply's context.id
                # can be correlated back to the pending row it belongs to
                # (see whatsapp_webhook.py). Parse failure/absence is never
                # fatal to the send itself -- it already succeeded.
                provider_message_id = None
                try:
                    body = json.loads(response.read().decode("utf-8"))
                    messages = body.get("messages") or []
                    if messages:
                        provider_message_id = messages[0].get("id")
                except (ValueError, AttributeError):
                    pass
                return OutboundResult(status="SUCCESS", http_status=response.status, provider_message_id=provider_message_id)
        except urllib.error.HTTPError as error:
            return OutboundResult(status="FAILED", http_status=error.code, error="PROVIDER_HTTP_ERROR")
        except TimeoutError:
            return OutboundResult(status="FAILED", error="PROVIDER_TIMEOUT")
        except urllib.error.URLError:
            return OutboundResult(status="FAILED", error="PROVIDER_UNREACHABLE")


__all__ = ["OutboundResult", "WhatsAppOutboundClient", "WhatsAppOutboundConfig"]
