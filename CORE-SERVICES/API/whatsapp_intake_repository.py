from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TYPE_CHECKING

import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .auth_service import AuthenticatedIdentity, permissions_for_role  # noqa: E402

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


class WhatsAppIntakeRepository:
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def find_identity_by_sender_hash(self, sender_hash: str) -> AuthenticatedIdentity | None:
        rows = _json_query(
            "SELECT u.id AS user_id, u.email, u.username, u.status AS user_status, "
            "m.organization_id, o.code AS organization_code, m.role, m.status AS membership_status, "
            "m.data_scope_type, m.data_scope_value "
            "FROM whatsapp_sender_identity w "
            "JOIN users u ON u.id = w.user_id "
            "JOIN organization_memberships m ON m.user_id = u.id "
            "JOIN organizations o ON o.id = m.organization_id "
            f"WHERE w.sender_e164_sha256 = {_sql(sender_hash)} AND w.status = 'ACTIVE' "
            "AND u.status = 'ACTIVE' AND m.status = 'ACTIVE' "
            "ORDER BY m.created_at ASC LIMIT 1",
            self._runner,
        )
        if not rows:
            return None
        row = rows[0]
        return AuthenticatedIdentity(
            user_id=row["user_id"],
            email=row.get("email"),
            username=row.get("username"),
            organization_id=row["organization_id"],
            organization_code=row["organization_code"],
            role=row["role"],
            permissions=permissions_for_role(row["role"]),
            data_scope_type=row.get("data_scope_type"),
            data_scope_value=row.get("data_scope_value"),
        )

    def find_pending_by_delivery_key(self, provider: str, provider_message_id: str, sender_user_id: str) -> dict | None:
        rows = _json_query(
            "SELECT * FROM whatsapp_intake_pending "
            f"WHERE provider = {_sql(provider)} AND provider_message_id = {_sql(provider_message_id)} "
            f"AND sender_user_id = {_sql(sender_user_id)} LIMIT 1",
            self._runner,
        )
        return _decode_row(rows[0]) if rows else None

    def find_pending_by_confirmation_id(self, confirmation_id: str, sender_user_id: str) -> dict | None:
        rows = _json_query(
            "SELECT * FROM whatsapp_intake_pending "
            f"WHERE confirmation_id = {_sql(confirmation_id)} AND sender_user_id = {_sql(sender_user_id)} LIMIT 1",
            self._runner,
        )
        return _decode_row(rows[0]) if rows else None

    def find_latest_actionable_pending(self, sender_user_id: str) -> dict | None:
        # MWO-025J2 note: kept for callers that intentionally want "the one
        # most recent row" (e.g. tests exercising legacy behavior directly).
        # whatsapp_intake_service.py's own confirmation flow now uses
        # find_actionable_pending_list() instead, so it can detect
        # ambiguity (2+ actionable rows) rather than silently picking one.
        rows = _json_query(
            "SELECT * FROM whatsapp_intake_pending "
            f"WHERE sender_user_id = {_sql(sender_user_id)} "
            "AND state IN ('READY_FOR_CONFIRMATION', 'NEEDS_INFORMATION', 'CONFIRMED') "
            "ORDER BY created_at DESC LIMIT 1",
            self._runner,
        )
        return _decode_row(rows[0]) if rows else None

    def find_actionable_pending_list(self, sender_user_id: str) -> list[dict]:
        rows = _json_query(
            "SELECT * FROM whatsapp_intake_pending "
            f"WHERE sender_user_id = {_sql(sender_user_id)} "
            "AND state IN ('READY_FOR_CONFIRMATION', 'NEEDS_INFORMATION', 'CONFIRMED') "
            "ORDER BY created_at DESC",
            self._runner,
        )
        return [_decode_row(row) for row in rows]

    def find_pending_by_outbound_message_id(self, provider_message_id: str, sender_user_id: str) -> dict | None:
        # MWO-025J2 -- resolves a Meta inbound message's context.id (the
        # provider_message_id of the AI5R outbound message being replied
        # to) back to the exact pending row it belongs to, so "YA" never
        # has to guess which conversation a reply is for when a context
        # link is available.
        rows = _json_query(
            "SELECT * FROM whatsapp_intake_pending "
            f"WHERE last_outbound_provider_message_id = {_sql(provider_message_id)} "
            f"AND sender_user_id = {_sql(sender_user_id)} LIMIT 1",
            self._runner,
        )
        return _decode_row(rows[0]) if rows else None

    def create_pending(self, payload: dict[str, Any]) -> dict:
        raw = self._runner.query_scalar(
            "WITH ins AS ("
            "INSERT INTO whatsapp_intake_pending ("
            "provider, provider_message_id, sender_user_id, organization_id, received_at, original_message, "
            "detected_domain, structured_payload, validation_result, state, normalized_payload_hash, "
            "provider_payload, reply_text"
            ") VALUES ("
            f"{_sql(payload['provider'])}, {_sql(payload['provider_message_id'])}, {_sql(payload['sender_user_id'])}, "
            f"{_sql(payload.get('organization_id'))}, "
            f"COALESCE({_sql(payload.get('received_at'))}::timestamptz, NOW()), "
            f"{_sql(payload.get('original_message'))}, {_sql(payload.get('detected_domain'))}, "
            f"{_sql(json.dumps(payload.get('structured_payload') or {}, sort_keys=True))}::jsonb, "
            f"{_sql(json.dumps(payload.get('validation_result') or {}, sort_keys=True))}::jsonb, "
            f"{_sql(payload['state'])}, {_sql(payload['normalized_payload_hash'])}, "
            f"{_sql(json.dumps(payload.get('provider_payload') or {}, sort_keys=True))}::jsonb, {_sql(payload.get('reply'))}"
            ") ON CONFLICT (provider, provider_message_id, sender_user_id) DO UPDATE SET "
            "updated_at = NOW() RETURNING *"
            ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ins t;"
        )
        rows = json.loads(raw or "[]")
        if not rows:
            raise RuntimeError("WhatsApp intake insert returned no row")
        return _decode_row(rows[0])

    def transition_pending(
        self,
        intake_id: str,
        *,
        state: str,
        confirmed_by: str | None = None,
        validation_result: dict[str, Any] | None = None,
        structured_payload: dict[str, Any] | None = None,
        last_outbound_provider_message_id: str | None = None,
    ) -> dict:
        validation_sql = (
            f", validation_result = {_sql(json.dumps(validation_result, sort_keys=True))}::jsonb"
            if validation_result is not None
            else ""
        )
        payload_sql = (
            f", structured_payload = {_sql(json.dumps(structured_payload, sort_keys=True))}::jsonb"
            if structured_payload is not None
            else ""
        )
        outbound_id_sql = (
            f", last_outbound_provider_message_id = {_sql(last_outbound_provider_message_id)}"
            if last_outbound_provider_message_id is not None
            else ""
        )
        confirmed_sql = (
            f", confirmed_by = {_sql(confirmed_by)}, confirmed_at = CASE WHEN confirmed_at IS NULL THEN NOW() ELSE confirmed_at END"
            if confirmed_by is not None and state == "CONFIRMED"
            else ""
        )
        raw = self._runner.query_scalar(
            "WITH upd AS ("
            f"UPDATE whatsapp_intake_pending SET state = {_sql(state)}, updated_at = NOW()"
            f"{confirmed_sql}{validation_sql}{payload_sql}{outbound_id_sql} WHERE intake_id = {_sql(intake_id)} RETURNING *"
            ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM upd t;"
        )
        rows = json.loads(raw or "[]")
        if not rows:
            raise RuntimeError("WhatsApp intake transition returned no row")
        return _decode_row(rows[0])


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("structured_payload", "validation_result", "provider_payload"):
        value = row.get(key)
        if isinstance(value, str):
            row[key] = json.loads(value)
    return row


__all__ = ["WhatsAppIntakeRepository"]
