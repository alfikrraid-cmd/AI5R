"""Resend HTTP client using Python standard library urllib.request."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("auth.resend_client")

DEFAULT_RESEND_API_BASE_URL = "https://api.resend.com"
DEFAULT_FROM_EMAIL = "noreply@mail.osa-system.com"
DEFAULT_FROM_NAME = "AI5R LTSA"
DEFAULT_APP_PUBLIC_URL = "https://osa-system.com"


@dataclass(frozen=True, slots=True)
class ResendResult:
    status: str  # "SUCCESS" | "FAILED" | "SKIPPED"
    http_status: int | None = None
    error: str | None = None
    email_id: str | None = None


@dataclass(slots=True)
class ResendConfig:
    api_key: str | None = None
    base_url: str = DEFAULT_RESEND_API_BASE_URL
    from_email: str = DEFAULT_FROM_EMAIL
    from_name: str = DEFAULT_FROM_NAME
    app_public_url: str = DEFAULT_APP_PUBLIC_URL
    timeout: int = 10


class ResendClient:
    def __init__(self, config: ResendConfig | None = None) -> None:
        if config is not None:
            self.config = config
        else:
            self.config = ResendConfig(
                api_key=os.getenv("RESEND_API_KEY"),
                base_url=os.getenv("RESEND_API_BASE_URL", DEFAULT_RESEND_API_BASE_URL),
                from_email=os.getenv("RESEND_FROM_EMAIL", DEFAULT_FROM_EMAIL),
                from_name=os.getenv("RESEND_FROM_NAME", DEFAULT_FROM_NAME),
                app_public_url=os.getenv("APP_PUBLIC_URL", os.getenv("AI5R_DASHBOARD_PUBLIC_URL", DEFAULT_APP_PUBLIC_URL)),
                timeout=int(os.getenv("RESEND_TIMEOUT_SECONDS", "10")),
            )

    @property
    def sender(self) -> str:
        name = (self.config.from_name or "").strip()
        email = (self.config.from_email or "").strip()
        if name:
            return f"{name} <{email}>"
        return email

    def send_email(
        self,
        *,
        to: str,
        subject: str,
        html: str,
        text: str,
    ) -> ResendResult:
        if not self.config.api_key:
            logger.warning("Resend send skipped: RESEND_API_KEY is not configured")
            return ResendResult(status="SKIPPED", error="RESEND_API_KEY_UNSET")

        url = f"{self.config.base_url.rstrip('/')}/emails"
        payload = {
            "from": self.sender,
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AI5R-LTSA/1.0",
        }
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout) as response:
                body = response.read().decode("utf-8")
                parsed = json.loads(body) if body else {}
                return ResendResult(
                    status="SUCCESS",
                    http_status=response.status,
                    email_id=parsed.get("id"),
                )
        except urllib.error.HTTPError as error:
            logger.error("Resend API HTTP error: status=%s", error.code)
            return ResendResult(
                status="FAILED",
                http_status=error.code,
                error="RESEND_HTTP_ERROR",
            )
        except urllib.error.URLError as error:
            logger.error("Resend API connection error: %s", error.reason)
            return ResendResult(
                status="FAILED",
                error="RESEND_CONNECTION_ERROR",
            )
        except Exception:
            logger.error("Unexpected error sending email via Resend")
            return ResendResult(
                status="FAILED",
                error="UNEXPECTED_ERROR",
            )


__all__ = [
    "DEFAULT_APP_PUBLIC_URL",
    "DEFAULT_FROM_EMAIL",
    "DEFAULT_FROM_NAME",
    "DEFAULT_RESEND_API_BASE_URL",
    "ResendClient",
    "ResendConfig",
    "ResendResult",
]
