"""MWO-LTSA-AUTH-001 -- bootstrap the FIRST TAP_ADMIN user.

Reuses DatabaseConfig/DatabaseRunner (ltsa_pump_inventory_db_upsert.py,
unmodified) and API.auth_repository/API.auth_password (this MWO) --
no second database-access layer, no invented password scheme.

Same CLI convention ltsa_pump_inventory_db_upsert.py::main() already
establishes (argparse, --env-file/--compose-file, def main() -> int,
`if __name__ == "__main__": raise SystemExit(main())`).

Security requirements this script exists to satisfy (never relaxed):
  - Credentials come from the environment only -- never a source-code
    default, never a CLI argument (which would leak into shell history/
    process listings).
  - Idempotent: running it again with the same email is always safe.
  - Never silently resets an existing user's password -- if the email
    already exists, this script only ensures a TAP_ADMIN membership
    exists for them; it never touches password_hash.
  - Auditable: every outcome is a distinct, printed, human-readable
    message -- created / membership-granted-to-existing-user / already-
    fully-provisioned -- never a bare "OK".
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_AI5R_ROOT = Path(__file__).resolve().parents[2].parent
_CORE_SERVICES_DIR = _AI5R_ROOT / "CORE-SERVICES"
_AI5R_SDK_DIR = _AI5R_ROOT / "AI5R-SDK"
for _path in (_CORE_SERVICES_DIR, _AI5R_SDK_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from API.auth_password import hash_password  # noqa: E402
from API.auth_repository import AuthRepository  # noqa: E402
from ltsa_pump_inventory_db_upsert import DatabaseConfig, DatabaseRunner  # noqa: E402

_TAP_ORGANIZATION_CODE = "TAP"
_ADMIN_ROLE = "TAP_ADMIN"


def bootstrap_admin(runner: "DatabaseRunner", email: str, password: str) -> str:
    repository = AuthRepository(runner)

    organization_id = repository.find_organization_by_code(_TAP_ORGANIZATION_CODE)
    if organization_id is None:
        raise RuntimeError(
            f"Organization '{_TAP_ORGANIZATION_CODE}' does not exist -- "
            "apply PRODUCTS/LTSA-BRAIN/DATABASE/MIGRATIONS/007_create_ltsa_auth_foundation.sql first."
        )

    existing_user = repository.find_user_by_email(email)
    if existing_user is not None:
        membership = repository.find_membership(existing_user.id, organization_id)
        if membership is not None:
            return f"User '{email}' already exists with a {membership.role} membership in {_TAP_ORGANIZATION_CODE} -- no changes made (password untouched)."
        repository.create_membership(user_id=existing_user.id, organization_id=organization_id, role=_ADMIN_ROLE)
        return f"User '{email}' already existed; granted {_ADMIN_ROLE} membership in {_TAP_ORGANIZATION_CODE} (password untouched)."

    user_id = repository.create_user(email=email, password_hash=hash_password(password))
    repository.create_membership(user_id=user_id, organization_id=organization_id, role=_ADMIN_ROLE)
    return f"Created new {_ADMIN_ROLE} user '{email}' in {_TAP_ORGANIZATION_CODE}."


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap the first TAP_ADMIN user. Credentials come from environment variables only."
    )
    parser.add_argument("--env-file", type=Path, default=None)
    parser.add_argument("--compose-file", type=Path, default=None)
    args = parser.parse_args()

    email = os.getenv("AI5R_BOOTSTRAP_ADMIN_EMAIL")
    password = os.getenv("AI5R_BOOTSTRAP_ADMIN_PASSWORD")
    if not email or not password:
        print(
            "AI5R_BOOTSTRAP_ADMIN_EMAIL and AI5R_BOOTSTRAP_ADMIN_PASSWORD must both be set "
            "in the environment. No default credentials exist -- refusing to proceed.",
            file=sys.stderr,
        )
        return 1

    runtime_dir = Path(__file__).resolve().parents[2].parent / "CORE-SERVICES" / "RUNTIME"
    env_file = args.env_file or runtime_dir / ".env.verify.local"
    compose_file = args.compose_file or runtime_dir / "compose.yaml"

    direct_host = os.getenv("AI5R_POSTGRES_HOST")
    if direct_host:
        config = DatabaseConfig(
            host=direct_host,
            port=int(os.getenv("AI5R_POSTGRES_PORT", "5432")),
            user=os.getenv("AI5R_POSTGRES_USER", "ai5r"),
            password=os.getenv("AI5R_POSTGRES_PASSWORD", ""),
            database=os.getenv("AI5R_LTSA_POSTGRES_DB", "ai5r_runtime"),
        )
    else:
        config = DatabaseConfig(
            env_file=env_file, compose_file=compose_file, database=os.getenv("AI5R_LTSA_POSTGRES_DB", "ai5r_runtime")
        )

    runner = DatabaseRunner(config)

    try:
        outcome = bootstrap_admin(runner, email, password)
    except RuntimeError as error:
        print(f"FAILED: {error}", file=sys.stderr)
        return 1

    print(outcome)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
