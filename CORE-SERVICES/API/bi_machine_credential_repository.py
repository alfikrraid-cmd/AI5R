"""LTSA_POWER_BI_R1C -- Repository for Power BI Machine Credentials & Audit Ledger.

Provides both:
1. BiMachineCredentialPostgresRepository (real Postgres backed via DatabaseRunner)
2. InMemoryBiMachineCredentialRepository (in-memory implementation for tests/offline)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import sys

_INGESTION_DIR = Path(__file__).resolve().parents[2] / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"
if str(_INGESTION_DIR) not in sys.path:
    sys.path.insert(0, str(_INGESTION_DIR))

from ltsa_pump_inventory_db_upsert import _json_query, _sql  # noqa: E402

from .bi_machine_auth_service import (  # noqa: E402
    BiMachineCredentialRecord,
    BiMachineCredentialRepositoryProtocol,
)

if TYPE_CHECKING:
    from ltsa_pump_inventory_db_upsert import DatabaseRunner


def _parse_iso(val: Any) -> datetime | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    try:
        # Replace space with T for ISO format if needed
        s = str(val).replace(" ", "T")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _row_to_credential(row: dict) -> BiMachineCredentialRecord:
    return BiMachineCredentialRecord(
        id=str(row["id"]),
        client_id=str(row["client_id"]),
        description=row.get("description"),
        organization_id=str(row["organization_id"]),
        organization_code=str(row.get("organization_code", "TAP")),
        role=str(row.get("role", "BI_READER")),
        primary_secret_hash=str(row["primary_secret_hash"]),
        primary_created_at=_parse_iso(row.get("primary_created_at")) or datetime.now(timezone.utc),
        secondary_secret_hash=row.get("secondary_secret_hash"),
        secondary_created_at=_parse_iso(row.get("secondary_created_at")),
        secondary_expires_at=_parse_iso(row.get("secondary_expires_at")),
        status=str(row.get("status", "ACTIVE")),
        revoked_at=_parse_iso(row.get("revoked_at")),
        revoked_by=row.get("revoked_by"),
        revocation_reason=row.get("revocation_reason"),
        last_used_at=_parse_iso(row.get("last_used_at")),
        created_at=_parse_iso(row.get("created_at")) or datetime.now(timezone.utc),
        updated_at=_parse_iso(row.get("updated_at")) or datetime.now(timezone.utc),
    )


class BiMachineCredentialPostgresRepository(BiMachineCredentialRepositoryProtocol):
    def __init__(self, runner: "DatabaseRunner") -> None:
        self._runner = runner

    def get_credential_by_client_id(self, client_id: str) -> BiMachineCredentialRecord | None:
        rows = _json_query(
            "SELECT c.*, o.code AS organization_code "
            "FROM public.ltsa_bi_machine_credential c "
            "JOIN public.organizations o ON o.id = c.organization_id "
            f"WHERE c.client_id = {_sql(client_id)} "
            "LIMIT 1",
            self._runner,
        )
        return _row_to_credential(rows[0]) if rows else None

    def create_credential(
        self,
        client_id: str,
        secret_hash: str,
        organization_id: str,
        description: str | None,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH ins AS ("
                "INSERT INTO public.ltsa_bi_machine_credential ("
                "client_id, description, organization_id, role, primary_secret_hash, status"
                ") VALUES ("
                f"{_sql(client_id)}, {_sql(description)}, {_sql(organization_id)}, 'BI_READER', {_sql(secret_hash)}, 'ACTIVE'"
                ") RETURNING * "
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
                "SELECT ins.*, o.code AS organization_code FROM ins "
                "JOIN public.organizations o ON o.id = ins.organization_id"
                ") t;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError(f"Failed to create credential for {client_id}")

        self.record_audit_event(
            client_id=client_id,
            event_type="CREDENTIAL_CREATED",
            actor=actor,
            credential_id=rows[0]["id"],
            details={"description": description, "organization_id": organization_id},
        )
        return _row_to_credential(rows[0])

    def rotate_credential(
        self,
        client_id: str,
        new_secret_hash: str,
        grace_days: int,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE public.ltsa_bi_machine_credential SET "
                f"secondary_secret_hash = {_sql(new_secret_hash)}, "
                "secondary_created_at = NOW(), "
                f"secondary_expires_at = NOW() + INTERVAL '{int(grace_days)} days', "
                "updated_at = NOW() "
                f"WHERE client_id = {_sql(client_id)} AND status = 'ACTIVE' "
                "RETURNING * "
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
                "SELECT upd.*, o.code AS organization_code FROM upd "
                "JOIN public.organizations o ON o.id = upd.organization_id"
                ") t;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError(f"Cannot rotate: active credential with client_id '{client_id}' not found")

        self.record_audit_event(
            client_id=client_id,
            event_type="CREDENTIAL_ROTATED",
            actor=actor,
            credential_id=rows[0]["id"],
            details={"grace_days": grace_days, "secondary_expires_at": rows[0].get("secondary_expires_at")},
        )
        return _row_to_credential(rows[0])

    def promote_secondary_secret(
        self,
        client_id: str,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE public.ltsa_bi_machine_credential SET "
                "primary_secret_hash = secondary_secret_hash, "
                "primary_created_at = NOW(), "
                "secondary_secret_hash = NULL, "
                "secondary_created_at = NULL, "
                "secondary_expires_at = NULL, "
                "updated_at = NOW() "
                f"WHERE client_id = {_sql(client_id)} AND secondary_secret_hash IS NOT NULL AND status = 'ACTIVE' "
                "RETURNING * "
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
                "SELECT upd.*, o.code AS organization_code FROM upd "
                "JOIN public.organizations o ON o.id = upd.organization_id"
                ") t;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError(f"Cannot promote: credential '{client_id}' has no secondary secret to promote")

        self.record_audit_event(
            client_id=client_id,
            event_type="CREDENTIAL_ROTATED",
            actor=actor,
            credential_id=rows[0]["id"],
            details={"action": "PROMOTE_SECONDARY_TO_PRIMARY"},
        )
        return _row_to_credential(rows[0])

    def revoke_credential(
        self,
        client_id: str,
        reason: str,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rows = json.loads(
            self._runner.query_scalar(
                "WITH upd AS ("
                "UPDATE public.ltsa_bi_machine_credential SET "
                "status = 'REVOKED', "
                "revoked_at = NOW(), "
                f"revoked_by = {_sql(actor)}, "
                f"revocation_reason = {_sql(reason)}, "
                "secondary_secret_hash = NULL, "
                "secondary_created_at = NULL, "
                "secondary_expires_at = NULL, "
                "updated_at = NOW() "
                f"WHERE client_id = {_sql(client_id)} "
                "RETURNING * "
                ") SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ("
                "SELECT upd.*, o.code AS organization_code FROM upd "
                "JOIN public.organizations o ON o.id = upd.organization_id"
                ") t;"
            )
            or "[]"
        )
        if not rows:
            raise RuntimeError(f"Cannot revoke: credential with client_id '{client_id}' not found")

        self.record_audit_event(
            client_id=client_id,
            event_type="CREDENTIAL_REVOKED",
            actor=actor,
            credential_id=rows[0]["id"],
            details={"reason": reason},
        )
        return _row_to_credential(rows[0])

    def record_audit_event(
        self,
        client_id: str,
        event_type: str,
        actor: str,
        credential_id: str | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        details_json = json.dumps(details or {})
        try:
            self._runner.execute_script(
                "INSERT INTO public.ltsa_bi_credential_audit_event ("
                "credential_id, client_id, event_type, actor, source_ip, user_agent, details"
                ") VALUES ("
                f"{_sql(credential_id)}, {_sql(client_id)}, {_sql(event_type)}, "
                f"{_sql(actor)}, {_sql(source_ip)}, {_sql(user_agent)}, {_sql(details_json)}::jsonb"
                ");"
            )
        except Exception:
            # Audit failures must not break operational flow if DB table is unpopulated
            pass

    def record_last_used(self, client_id: str) -> None:
        try:
            self._runner.execute_script(
                f"UPDATE public.ltsa_bi_machine_credential SET last_used_at = NOW() WHERE client_id = {_sql(client_id)};"
            )
        except Exception:
            pass

    def list_credentials(self) -> list[BiMachineCredentialRecord]:
        rows = _json_query(
            "SELECT c.*, o.code AS organization_code "
            "FROM public.ltsa_bi_machine_credential c "
            "JOIN public.organizations o ON o.id = c.organization_id "
            "ORDER BY c.created_at ASC",
            self._runner,
        )
        return [_row_to_credential(r) for r in rows]


class InMemoryBiMachineCredentialRepository(BiMachineCredentialRepositoryProtocol):
    """In-memory implementation for unit testing and offline test execution."""

    def __init__(self) -> None:
        self.credentials: dict[str, BiMachineCredentialRecord] = {}
        self.audit_events: list[dict[str, Any]] = []

    def get_credential_by_client_id(self, client_id: str) -> BiMachineCredentialRecord | None:
        return self.credentials.get(client_id)

    def create_credential(
        self,
        client_id: str,
        secret_hash: str,
        organization_id: str,
        description: str | None,
        actor: str,
    ) -> BiMachineCredentialRecord:
        now = datetime.now(timezone.utc)
        record = BiMachineCredentialRecord(
            id=f"cred-{len(self.credentials)+1}",
            client_id=client_id,
            description=description,
            organization_id=organization_id,
            organization_code="TAP",
            role="BI_READER",
            primary_secret_hash=secret_hash,
            primary_created_at=now,
            secondary_secret_hash=None,
            secondary_created_at=None,
            secondary_expires_at=None,
            status="ACTIVE",
            revoked_at=None,
            revoked_by=None,
            revocation_reason=None,
            last_used_at=None,
            created_at=now,
            updated_at=now,
        )
        self.credentials[client_id] = record
        self.record_audit_event(client_id, "CREDENTIAL_CREATED", actor, record.id, details={"description": description})
        return record

    def rotate_credential(
        self,
        client_id: str,
        new_secret_hash: str,
        grace_days: int,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rec = self.credentials.get(client_id)
        if not rec or rec.status != "ACTIVE":
            raise RuntimeError(f"Cannot rotate: active credential with client_id '{client_id}' not found")
        now = datetime.now(timezone.utc)
        updated = BiMachineCredentialRecord(
            id=rec.id,
            client_id=rec.client_id,
            description=rec.description,
            organization_id=rec.organization_id,
            organization_code=rec.organization_code,
            role=rec.role,
            primary_secret_hash=rec.primary_secret_hash,
            primary_created_at=rec.primary_created_at,
            secondary_secret_hash=new_secret_hash,
            secondary_created_at=now,
            secondary_expires_at=now + timedelta(days=grace_days),
            status=rec.status,
            revoked_at=rec.revoked_at,
            revoked_by=rec.revoked_by,
            revocation_reason=rec.revocation_reason,
            last_used_at=rec.last_used_at,
            created_at=rec.created_at,
            updated_at=now,
        )
        self.credentials[client_id] = updated
        self.record_audit_event(client_id, "CREDENTIAL_ROTATED", actor, rec.id, details={"grace_days": grace_days})
        return updated

    def promote_secondary_secret(
        self,
        client_id: str,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rec = self.credentials.get(client_id)
        if not rec or not rec.secondary_secret_hash or rec.status != "ACTIVE":
            raise RuntimeError(f"Cannot promote: credential '{client_id}' has no secondary secret to promote")
        now = datetime.now(timezone.utc)
        updated = BiMachineCredentialRecord(
            id=rec.id,
            client_id=rec.client_id,
            description=rec.description,
            organization_id=rec.organization_id,
            organization_code=rec.organization_code,
            role=rec.role,
            primary_secret_hash=rec.secondary_secret_hash,
            primary_created_at=now,
            secondary_secret_hash=None,
            secondary_created_at=None,
            secondary_expires_at=None,
            status=rec.status,
            revoked_at=rec.revoked_at,
            revoked_by=rec.revoked_by,
            revocation_reason=rec.revocation_reason,
            last_used_at=rec.last_used_at,
            created_at=rec.created_at,
            updated_at=now,
        )
        self.credentials[client_id] = updated
        self.record_audit_event(client_id, "CREDENTIAL_ROTATED", actor, rec.id, details={"action": "PROMOTE"})
        return updated

    def revoke_credential(
        self,
        client_id: str,
        reason: str,
        actor: str,
    ) -> BiMachineCredentialRecord:
        rec = self.credentials.get(client_id)
        if not rec:
            raise RuntimeError(f"Cannot revoke: credential with client_id '{client_id}' not found")
        now = datetime.now(timezone.utc)
        updated = BiMachineCredentialRecord(
            id=rec.id,
            client_id=rec.client_id,
            description=rec.description,
            organization_id=rec.organization_id,
            organization_code=rec.organization_code,
            role=rec.role,
            primary_secret_hash=rec.primary_secret_hash,
            primary_created_at=rec.primary_created_at,
            secondary_secret_hash=None,
            secondary_created_at=None,
            secondary_expires_at=None,
            status="REVOKED",
            revoked_at=now,
            revoked_by=actor,
            revocation_reason=reason,
            last_used_at=rec.last_used_at,
            created_at=rec.created_at,
            updated_at=now,
        )
        self.credentials[client_id] = updated
        self.record_audit_event(client_id, "CREDENTIAL_REVOKED", actor, rec.id, details={"reason": reason})
        return updated

    def record_audit_event(
        self,
        client_id: str,
        event_type: str,
        actor: str,
        credential_id: str | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.audit_events.append(
            {
                "client_id": client_id,
                "event_type": event_type,
                "actor": actor,
                "credential_id": credential_id,
                "source_ip": source_ip,
                "user_agent": user_agent,
                "details": details or {},
                "occurred_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def record_last_used(self, client_id: str) -> None:
        rec = self.credentials.get(client_id)
        if rec:
            now = datetime.now(timezone.utc)
            self.credentials[client_id] = BiMachineCredentialRecord(
                id=rec.id,
                client_id=rec.client_id,
                description=rec.description,
                organization_id=rec.organization_id,
                organization_code=rec.organization_code,
                role=rec.role,
                primary_secret_hash=rec.primary_secret_hash,
                primary_created_at=rec.primary_created_at,
                secondary_secret_hash=rec.secondary_secret_hash,
                secondary_created_at=rec.secondary_created_at,
                secondary_expires_at=rec.secondary_expires_at,
                status=rec.status,
                revoked_at=rec.revoked_at,
                revoked_by=rec.revoked_by,
                revocation_reason=rec.revocation_reason,
                last_used_at=now,
                created_at=rec.created_at,
                updated_at=rec.updated_at,
            )

    def list_credentials(self) -> list[BiMachineCredentialRecord]:
        return list(self.credentials.values())


__all__ = [
    "BiMachineCredentialPostgresRepository",
    "InMemoryBiMachineCredentialRepository",
]
