"""Password reset service orchestrating token creation, validation, and email dispatch."""
from __future__ import annotations

import hashlib
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from .auth_password import hash_password, validate_password_policy, verify_password
from .resend_client import ResendClient

if TYPE_CHECKING:
    from .auth_repository import AuthRepository
    from .password_reset_repository import PasswordResetRepositoryProtocol
    from .record_change_history_repository import RecordChangeHistoryRepository

logger = logging.getLogger("auth.password_reset")

_DUMMY_PASSWORD_HASH = "scrypt$16384$8$1$c2FsdHNhbHQxMjM0NQ==$ZHVtbXloYXNoZHVtbXloYXNoZHVtbXloYXNoZHVtbXk="


def _reset_password_email(reset_url: str) -> tuple[str, str, str]:
    # Build email content
    subject = "Reset Password — AI5R LTSA"
    html = (
        "<div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 24px;\">"
        "<h2 style=\"color: #0f172a; margin-bottom: 16px;\">AI5R LTSA Engineering</h2>"
        "<p>A request was received to reset your password for your AI5R LTSA account.</p>"
        "<p style=\"margin: 24px 0;\">"
        f"<a href=\"{reset_url}\" style=\"background-color: #0284c7; color: #ffffff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 500; display: inline-block;\">Reset Password</a>"
        "</p>"
        "<p style=\"font-size: 14px; color: #64748b;\">This password reset link is valid for 15 minutes.</p>"
        "<p style=\"font-size: 14px; color: #64748b;\">If you did not request a password reset, you can safely ignore this email. Your password will not change.</p>"
        "<hr style=\"border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #94a3b8;\">AI5R LTSA — Asset intelligence for rotating equipment</p>"
        "</div>"
    )
    text = (
        "AI5R LTSA Engineering\n\n"
        "A request was received to reset your password for your AI5R LTSA account.\n\n"
        f"Reset Password: {reset_url}\n\n"
        "This password reset link is valid for 15 minutes.\n\n"
        "If you did not request a password reset, you can safely ignore this email. Your password will not change.\n"
    )

    return subject, html, text


def _set_password_email(reset_url: str) -> tuple[str, str, str]:
    subject = "Set your password — AI5R LTSA"
    html = (
        "<div style=\"font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; max-width: 600px; margin: 0 auto; padding: 24px;\">"
        "<h2 style=\"color: #0f172a; margin-bottom: 16px;\">AI5R LTSA Engineering</h2>"
        "<p>An AI5R LTSA account has been created for you. Choose your password to activate sign-in.</p>"
        "<p style=\"margin: 24px 0;\">"
        f"<a href=\"{reset_url}\" style=\"background-color: #0284c7; color: #ffffff; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: 500; display: inline-block;\">Set Password</a>"
        "</p>"
        "<p style=\"font-size: 14px; color: #64748b;\">This link is valid for 15 minutes. If it expires, ask your LTSA administrator to send a new one, or use Forgot Password on the sign-in page.</p>"
        "<hr style=\"border: 0; border-top: 1px solid #e2e8f0; margin: 24px 0;\" />"
        "<p style=\"font-size: 12px; color: #94a3b8;\">AI5R LTSA — Asset intelligence for rotating equipment</p>"
        "</div>"
    )
    text = (
        "AI5R LTSA Engineering\n\n"
        "An AI5R LTSA account has been created for you. Choose your password to activate sign-in.\n\n"
        f"Set Password: {reset_url}\n\n"
        "This link is valid for 15 minutes. If it expires, ask your LTSA administrator to send a new one, "
        "or use Forgot Password on the sign-in page.\n"
    )
    return subject, html, text


class PasswordResetError(Exception):
    """Base exception for password reset operations."""


class InvalidTokenError(PasswordResetError):
    """Raised when a password reset token is invalid, expired, or already consumed."""


class RateLimitExceededError(PasswordResetError):
    """Raised when password reset rate limit is exceeded."""


class PasswordResetRateLimiter:
    """Fixed-window rate limiter (window = 15 minutes = 900 seconds).
    Limits to 5 requests per 15 minutes per IP and per normalized identifier.
    Matches the pattern in whatsapp_group_agent_service.InMemoryRateLimiter.
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 900) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._ip_counts: dict[tuple[int, str], int] = {}
        self._identifier_counts: dict[tuple[int, str], int] = {}

    def allow(self, *, client_ip: str | None, identifier: str | None = None) -> bool:
        now = time.time()
        window = int(now // self.window_seconds)

        if client_ip:
            ip_key = (window, client_ip)
            ip_count = self._ip_counts.get(ip_key, 0)
            if ip_count >= self.max_requests:
                return False

        norm_id = (identifier or "").strip().lower()
        if norm_id:
            id_key = (window, norm_id)
            id_count = self._identifier_counts.get(id_key, 0)
            if id_count >= self.max_requests:
                return False

        if client_ip:
            self._ip_counts[(window, client_ip)] = self._ip_counts.get((window, client_ip), 0) + 1
        if norm_id:
            self._identifier_counts[(window, norm_id)] = self._identifier_counts.get((window, norm_id), 0) + 1

        return True


class FailedPasswordAttemptLimiter:
    """LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- counts WRONG current-password
    attempts per user in a fixed 15-minute window; after max_failures the
    user is blocked until the window rolls over. A successful change clears
    the count. In-memory and per-process, like PasswordResetRateLimiter."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 900) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[tuple[int, str], int] = {}

    def _key(self, user_id: str) -> tuple[int, str]:
        return (int(time.time() // self.window_seconds), user_id)

    def is_blocked(self, user_id: str) -> bool:
        return self._failures.get(self._key(user_id), 0) >= self.max_failures

    def record_failure(self, user_id: str) -> None:
        key = self._key(user_id)
        self._failures[key] = self._failures.get(key, 0) + 1

    def clear(self, user_id: str) -> None:
        self._failures.pop(self._key(user_id), None)


class PasswordResetService:
    def __init__(
        self,
        *,
        auth_repository: AuthRepository,
        reset_repository: PasswordResetRepositoryProtocol,
        resend_client: ResendClient,
        rate_limiter: PasswordResetRateLimiter | None = None,
        change_history_repository: RecordChangeHistoryRepository | None = None,
    ) -> None:
        self.auth_repository = auth_repository
        self.reset_repository = reset_repository
        self.resend_client = resend_client
        self.rate_limiter = rate_limiter or PasswordResetRateLimiter()
        self.change_history_repository = change_history_repository

    def request_password_reset(self, identifier: str, *, client_ip: str | None = None) -> None:
        raw_id = (identifier or "").strip()

        # Rate limiting check
        if not self.rate_limiter.allow(client_ip=client_ip, identifier=raw_id):
            raise RateLimitExceededError("Too many password reset requests. Please try again later.")

        # Log allowed event without identifier, token, or account existence (Requirement 10)
        logger.info("password_reset_requested ip=%s", client_ip)

        if not raw_id:
            return

        # User resolution
        from .auth_service import _find_user_for_login
        user = _find_user_for_login(self.auth_repository, raw_id)

        # Constant-time mitigation if user not found, inactive, or has no email
        if user is None or user.status != "ACTIVE" or not user.email:
            verify_password("dummy_password", _DUMMY_PASSWORD_HASH)
            return

        # Valid active account with email
        self._issue_link(user, purpose="reset")

    def send_set_password_link(self, user_id: str) -> bool:
        """LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- admin onboarding: email the
        user a single-use link to choose their own password, using the same
        token store, TTL and reset-password endpoint as Forgot Password. The
        admin never sees a password. Returns False when the account cannot
        receive one (missing, inactive, no email) or the email could not be
        dispatched; never raises for those cases."""
        user = self.auth_repository.find_user_by_id(user_id)
        if user is None or user.status != "ACTIVE" or not user.email:
            return False
        return self._issue_link(user, purpose="set_password")

    def _issue_link(self, user, *, purpose: str) -> bool:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        self.reset_repository.create_reset_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        # Build reset link
        base_url = self.resend_client.config.app_public_url.rstrip("/")
        reset_url = f"{base_url}/reset-password?token={raw_token}"

        if purpose == "set_password":
            subject, html, text = _set_password_email(reset_url)
        else:
            subject, html, text = _reset_password_email(reset_url)

        try:
            self.resend_client.send_email(
                to=user.email,
                subject=subject,
                html=html,
                text=text,
            )
        except Exception:
            logger.error("Failed to dispatch password %s email", "set" if purpose == "set_password" else "reset")
            return False
        return True

    def reset_password(self, token: str, new_password: str, *, client_ip: str | None = None) -> None:
        raw_token = (token or "").strip()
        if not raw_token:
            raise InvalidTokenError("Invalid or expired password reset token")

        # LTSA_CHANGE_PASSWORD_FIRST_LOGIN_R2A -- global password policy. The
        # general rules run first; the username/email rules need the token's
        # user, read WITHOUT consuming the single-use token, so a rejected
        # password leaves the link usable for a second attempt.
        validate_password_policy(new_password)

        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        pending_user_id = self._pending_token_user_id(token_hash)
        if not pending_user_id:
            raise InvalidTokenError("Invalid or expired password reset token")
        pending_user = self.auth_repository.find_user_by_id(pending_user_id)
        if pending_user is not None:
            validate_password_policy(new_password, username=pending_user.username, email=pending_user.email)

        user_id = self.reset_repository.consume_reset_token(token_hash)
        if not user_id:
            raise InvalidTokenError("Invalid or expired password reset token")

        # The user chose this password through the verified recovery flow:
        # any forced first-login change is satisfied, and sessions issued
        # before now are ended (resolve_identity compares iat).
        new_hash = hash_password(new_password)
        self.auth_repository.update_password_hash(
            user_id,
            new_hash,
            updated_by=user_id,
            must_change_password=False,
            password_changed_at=datetime.now(timezone.utc).replace(microsecond=0),
        )

        # Log allowed completion event with internal user_id (Requirement 10)
        logger.info("password_reset_completed user_id=%s ip=%s", user_id, client_ip)

        if self.change_history_repository is not None:
            try:
                self.change_history_repository.append(
                    entity_type="user",
                    entity_id=user_id,
                    field_name="password",
                    old_value=None,
                    new_value="[REDACTED]",
                    changed_by=user_id,
                    reason="self_service_password_reset",
                )
            except Exception:
                pass

    def _pending_token_user_id(self, token_hash: str) -> str | None:
        """Read-only check that the token exists, is unused and unexpired.
        consume_reset_token remains the authoritative, atomic single-use
        gate; this only lets the policy check run before consumption."""
        record = self.reset_repository.get_token(token_hash)
        if not record or record.get("used_at") is not None:
            return None
        expires_at = record.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if expires_at is None:
            return None
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= datetime.now(timezone.utc):
            return None
        return record.get("user_id")


__all__ = [
    "InvalidTokenError",
    "PasswordResetError",
    "PasswordResetRateLimiter",
    "PasswordResetService",
    "RateLimitExceededError",
]
