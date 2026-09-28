"""LTSA_POWER_BI_R1C -- Restricted Operator CLI for Power BI Machine Credentials.

Provides operational management:
  CREATE  - Generate client_id & client_secret, store scrypt hash, display secret ONCE.
  ROTATE  - Generate secondary secret with overlapping grace period (zero downtime).
  PROMOTE - Promote verified secondary secret to primary.
  REVOKE  - Immediately deactivate credential.
  SHOW    - Display credential status & metadata without exposing secrets/hashes.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

_API_DIR = Path(__file__).resolve().parent
_CORE_DIR = _API_DIR.parent
_REPO_ROOT = _CORE_DIR.parent
_INGESTION_DIR = _REPO_ROOT / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"

for _path in (_API_DIR, _CORE_DIR, _REPO_ROOT, _INGESTION_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from ltsa_pump_inventory_db_upsert import DatabaseRunner  # noqa: E402

from .auth_repository import AuthRepository  # noqa: E402
from .bi_machine_auth_service import (  # noqa: E402
    BiMachineCredentialRepositoryProtocol,
    generate_client_id,
    generate_client_secret,
    hash_secret,
)
from .bi_machine_credential_repository import (  # noqa: E402
    BiMachineCredentialPostgresRepository,
)


def _get_default_repository() -> BiMachineCredentialRepositoryProtocol:
    from dependencies import _resolve_import_database_config  # noqa: E402

    config = _resolve_import_database_config()
    runner = DatabaseRunner(config)
    return BiMachineCredentialPostgresRepository(runner)


def _get_auth_repository() -> AuthRepository:
    from dependencies import _resolve_import_database_config  # noqa: E402

    config = _resolve_import_database_config()
    runner = DatabaseRunner(config)
    return AuthRepository(runner)


def cmd_create(args: argparse.Namespace, repo: BiMachineCredentialRepositoryProtocol) -> int:
    actor = args.actor or os.getenv("USER", "OPERATOR")
    org_code = args.org.upper()

    org_id = None
    if hasattr(repo, "_runner"):
        auth_repo = AuthRepository(repo._runner)
        org_id = auth_repo.find_organization_by_code(org_code)
    else:
        # In-memory or mock repository fallback
        org_id = getattr(repo, "default_org_id", "00000000-0000-0000-0000-000000000001")

    if not org_id:
        print(f"Error: Organization '{org_code}' not found.", file=sys.stderr)
        return 1

    client_id = generate_client_id()
    plaintext_secret = generate_client_secret()
    canonical_hash = hash_secret(plaintext_secret)

    record = repo.create_credential(
        client_id=client_id,
        secret_hash=canonical_hash,
        organization_id=org_id,
        description=args.desc,
        actor=actor,
    )

    print("=" * 68)
    print("POWER BI MACHINE CREDENTIAL CREATED")
    print("=" * 68)
    print(f"Client ID:      {record.client_id}")
    print(f"Client Secret:  {plaintext_secret}")
    print(f"Organization:   {org_code}")
    print(f"Role:           {record.role}")
    print(f"Status:         {record.status}")
    print(f"Description:    {record.description or '-'}")
    print("=" * 68)
    print("CRITICAL SECURITY NOTICE:")
    print("The client secret is displayed EXACTLY ONCE and cannot be recovered.")
    print("Store it directly in Power BI Service Data Source Credentials vault.")
    print("Never commit this secret to source control or embed it in PBIX files.")
    print("=" * 68)
    return 0


def cmd_rotate(args: argparse.Namespace, repo: BiMachineCredentialRepositoryProtocol) -> int:
    actor = args.actor or os.getenv("USER", "OPERATOR")
    client_id = args.client_id
    grace_days = args.grace_days

    plaintext_secret = generate_client_secret()
    canonical_hash = hash_secret(plaintext_secret)

    try:
        record = repo.rotate_credential(
            client_id=client_id,
            new_secret_hash=canonical_hash,
            grace_days=grace_days,
            actor=actor,
        )
    except Exception as e:
        print(f"Error rotating credential: {e}", file=sys.stderr)
        return 1

    print("=" * 68)
    print("POWER BI MACHINE CREDENTIAL ROTATED (SECONDARY SECRET ACTIVE)")
    print("=" * 68)
    print(f"Client ID:        {record.client_id}")
    print(f"New Secret:       {plaintext_secret}")
    print(f"Grace Period:     {grace_days} days")
    print(f"Secondary Expiry: {record.secondary_expires_at}")
    print("=" * 68)
    print("OPERATIONAL NOTICE:")
    print("Both the existing primary secret and this new secondary secret are")
    print("currently valid. Update Power BI Service credentials, verify scheduled")
    print("refresh, then execute:")
    print(f"  promote --client-id {record.client_id}")
    print("=" * 68)
    return 0


def cmd_promote(args: argparse.Namespace, repo: BiMachineCredentialRepositoryProtocol) -> int:
    actor = args.actor or os.getenv("USER", "OPERATOR")
    client_id = args.client_id

    try:
        record = repo.promote_secondary_secret(client_id=client_id, actor=actor)
    except Exception as e:
        print(f"Error promoting secondary secret: {e}", file=sys.stderr)
        return 1

    print("=" * 68)
    print("POWER BI MACHINE CREDENTIAL PROMOTED")
    print("=" * 68)
    print(f"Client ID:        {record.client_id}")
    print("Secondary secret has been promoted to Primary.")
    print("Prior primary secret and secondary secret slot are now cleared.")
    print("Zero-downtime rotation cycle complete.")
    print("=" * 68)
    return 0


def cmd_revoke(args: argparse.Namespace, repo: BiMachineCredentialRepositoryProtocol) -> int:
    actor = args.actor or os.getenv("USER", "OPERATOR")
    client_id = args.client_id
    reason = args.reason or "Revoked by operator"

    try:
        record = repo.revoke_credential(client_id=client_id, reason=reason, actor=actor)
    except Exception as e:
        print(f"Error revoking credential: {e}", file=sys.stderr)
        return 1

    print("=" * 68)
    print("POWER BI MACHINE CREDENTIAL REVOKED")
    print("=" * 68)
    print(f"Client ID:   {record.client_id}")
    print(f"Status:      {record.status}")
    print(f"Revoked At:  {record.revoked_at}")
    print(f"Reason:      {record.revocation_reason}")
    print("Authentication attempts with this credential will now fail immediately.")
    print("=" * 68)
    return 0


def cmd_show(args: argparse.Namespace, repo: BiMachineCredentialRepositoryProtocol) -> int:
    client_id = getattr(args, "client_id", None)
    if client_id:
        record = repo.get_credential_by_client_id(client_id)
        if not record:
            print(f"Credential '{client_id}' not found.", file=sys.stderr)
            return 1
        credentials = [record]
    else:
        credentials = repo.list_credentials()

    print("=" * 80)
    print(f"{'CLIENT ID':<30} {'ORG':<6} {'ROLE':<10} {'STATUS':<9} {'SECONDARY ACTIVE?':<18}")
    print("=" * 80)
    for c in credentials:
        has_secondary = "YES (exp: " + str(c.secondary_expires_at)[:10] + ")" if c.secondary_secret_hash else "NO"
        print(f"{c.client_id:<30} {c.organization_code:<6} {c.role:<10} {c.status:<9} {has_secondary:<18}")
    print("=" * 80)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bi_credential_cli",
        description="Restricted Operator CLI for LTSA Power BI Machine Credentials",
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # create
    p_create = subparsers.add_parser("create", help="Create a new Power BI machine credential")
    p_create.add_argument("--org", default="TAP", help="Organization code (default: TAP)")
    p_create.add_argument("--desc", default="Power BI Scheduled Refresh", help="Description")
    p_create.add_argument("--actor", help="Operator identity performing this action")

    # rotate
    p_rotate = subparsers.add_parser("rotate", help="Rotate secret with overlapping grace period")
    p_rotate.add_argument("--client-id", required=True, help="Client ID to rotate")
    p_rotate.add_argument("--grace-days", type=int, default=7, help="Grace days for secondary secret (default: 7)")
    p_rotate.add_argument("--actor", help="Operator identity performing this action")

    # promote
    p_promote = subparsers.add_parser("promote", help="Promote secondary secret to primary")
    p_promote.add_argument("--client-id", required=True, help="Client ID to promote")
    p_promote.add_argument("--actor", help="Operator identity performing this action")

    # revoke
    p_revoke = subparsers.add_parser("revoke", help="Revoke a machine credential immediately")
    p_revoke.add_argument("--client-id", required=True, help="Client ID to revoke")
    p_revoke.add_argument("--reason", default="Manual operator revocation", help="Revocation reason")
    p_revoke.add_argument("--actor", help="Operator identity performing this action")

    # show
    p_show = subparsers.add_parser("show", help="Show credential metadata (zero secrets exposed)")
    p_show.add_argument("--client-id", help="Client ID to show (omit to list all)")

    return parser


def main(argv: Sequence[str] | None = None, repository: BiMachineCredentialRepositoryProtocol | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    repo = repository or _get_default_repository()

    handlers = {
        "create": cmd_create,
        "rotate": cmd_rotate,
        "promote": cmd_promote,
        "revoke": cmd_revoke,
        "show": cmd_show,
    }

    handler = handlers.get(args.subcommand)
    if not handler:
        parser.print_help()
        return 1

    return handler(args, repo)


if __name__ == "__main__":
    raise SystemExit(main())
