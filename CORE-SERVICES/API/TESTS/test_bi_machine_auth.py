"""LTSA_POWER_BI_R1C -- Unit Tests for Power BI Machine Authentication & CLI.

Tests:
1. Canonical scrypt hash format: scrypt$16384$8$1$<salt_hex>$<hash_hex>.
2. Constant-time verification, rejection of malformed or invalid hashes.
3. Client ID and secret generation format & entropy.
4. Overlapping zero-downtime rotation lifecycle (Primary -> Secondary -> Promote).
5. Secondary grace period expiration.
6. Immediate revocation.
7. Role BI_READER constraint & path confinement.
8. Operator CLI (CREATE, ROTATE, PROMOTE, REVOKE, SHOW).
9. Plaintext secret displayed once, never persisted.
"""

from __future__ import annotations

import io
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.auth_service import AuthenticationError
from API.bi_credential_cli import main as cli_main
from API.bi_machine_auth_service import (
    authenticate_basic_credentials,
    generate_client_id,
    generate_client_secret,
    hash_secret,
    verify_secret,
)
from API.bi_machine_credential_repository import InMemoryBiMachineCredentialRepository


def test_hash_secret_canonical_format():
    secret = "sec_test_secret_12345"
    h = hash_secret(secret)
    parts = h.split("$")
    assert len(parts) == 6
    assert parts[0] == "scrypt"
    assert parts[1] == "16384"
    assert parts[2] == "8"
    assert parts[3] == "1"
    # salt_hex is 16 bytes = 32 hex chars
    assert len(parts[4]) == 32
    # hash_hex is 32 bytes = 64 hex chars
    assert len(parts[5]) == 64


def test_verify_secret_valid():
    secret = "sec_my_super_secret"
    h = hash_secret(secret)
    assert verify_secret(secret, h) is True
    assert verify_secret("wrong_secret", h) is False
    assert verify_secret("", h) is False
    assert verify_secret(secret, "malformed$hash") is False
    assert verify_secret(secret, "") is False


def test_generate_client_id_and_secret():
    client_id = generate_client_id()
    assert client_id.startswith("ltsa_bi_")
    assert len(client_id) == 32  # "ltsa_bi_" (8) + 24 hex chars

    secret = generate_client_secret()
    assert secret.startswith("sec_")
    assert len(secret) >= 48


def test_authenticate_basic_credentials_success():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = generate_client_id()
    secret = generate_client_secret()
    h = hash_secret(secret)

    repo.create_credential(
        client_id=client_id,
        secret_hash=h,
        organization_id="org-tap-uuid",
        description="Test Power BI",
        actor="TEST_SUITE",
    )

    identity = authenticate_basic_credentials(client_id, secret, repo)
    assert identity.username == client_id
    assert identity.role == "BI_READER"
    assert identity.permissions == frozenset({"bi.read"})
    assert identity.organization_id == "org-tap-uuid"


def test_authenticate_unknown_client_fails():
    repo = InMemoryBiMachineCredentialRepository()
    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        authenticate_basic_credentials("ltsa_bi_nonexistent", "sec_any", repo)


def test_authenticate_invalid_secret_fails():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = generate_client_id()
    secret = generate_client_secret()
    h = hash_secret(secret)

    repo.create_credential(
        client_id=client_id,
        secret_hash=h,
        organization_id="org-tap-uuid",
        description="Test Power BI",
        actor="TEST_SUITE",
    )

    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        authenticate_basic_credentials(client_id, "sec_wrong_secret", repo)


def test_overlapping_zero_downtime_rotation():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = generate_client_id()
    primary_secret = generate_client_secret()
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(primary_secret),
        organization_id="org-tap-uuid",
        description="Rotation test",
        actor="TEST_SUITE",
    )

    # 1. Primary secret works
    assert authenticate_basic_credentials(client_id, primary_secret, repo).role == "BI_READER"

    # 2. Rotate with 7 days grace period
    secondary_secret = generate_client_secret()
    repo.rotate_credential(
        client_id=client_id,
        new_secret_hash=hash_secret(secondary_secret),
        grace_days=7,
        actor="TEST_SUITE",
    )

    # BOTH primary and secondary work!
    assert authenticate_basic_credentials(client_id, primary_secret, repo).role == "BI_READER"
    assert authenticate_basic_credentials(client_id, secondary_secret, repo).role == "BI_READER"

    # 3. Promote secondary to primary
    repo.promote_secondary_secret(client_id=client_id, actor="TEST_SUITE")

    # Now secondary (new secret) is primary, old primary is invalid
    assert authenticate_basic_credentials(client_id, secondary_secret, repo).role == "BI_READER"
    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        authenticate_basic_credentials(client_id, primary_secret, repo)


def test_secondary_secret_grace_expiry():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = generate_client_id()
    primary_secret = generate_client_secret()
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(primary_secret),
        organization_id="org-tap-uuid",
        description="Expiry test",
        actor="TEST_SUITE",
    )

    secondary_secret = generate_client_secret()
    # Expire secondary in the past (-1 day)
    repo.rotate_credential(
        client_id=client_id,
        new_secret_hash=hash_secret(secondary_secret),
        grace_days=-1,
        actor="TEST_SUITE",
    )

    # Primary still works
    assert authenticate_basic_credentials(client_id, primary_secret, repo).role == "BI_READER"

    # Secondary is expired -> fails
    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        authenticate_basic_credentials(client_id, secondary_secret, repo)


def test_revocation_immediately_blocks_authentication():
    repo = InMemoryBiMachineCredentialRepository()
    client_id = generate_client_id()
    secret = generate_client_secret()
    repo.create_credential(
        client_id=client_id,
        secret_hash=hash_secret(secret),
        organization_id="org-tap-uuid",
        description="Revocation test",
        actor="TEST_SUITE",
    )

    # Works before revocation
    assert authenticate_basic_credentials(client_id, secret, repo).role == "BI_READER"

    # Revoke
    repo.revoke_credential(client_id=client_id, reason="Security review", actor="OPERATOR")

    # Immediate rejection
    with pytest.raises(AuthenticationError, match="Invalid credentials"):
        authenticate_basic_credentials(client_id, secret, repo)


def test_operator_cli_lifecycle():
    repo = InMemoryBiMachineCredentialRepository()

    # 1. CREATE
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        rc = cli_main(["create", "--org", "TAP", "--desc", "Finance Power BI", "--actor", "ADMIN"], repository=repo)
    assert rc == 0
    output = stdout.getvalue()
    assert "POWER BI MACHINE CREDENTIAL CREATED" in output
    assert "Client ID:" in output
    assert "Client Secret:" in output

    creds = repo.list_credentials()
    assert len(creds) == 1
    client_id = creds[0].client_id
    assert creds[0].status == "ACTIVE"

    # Check secret was never persisted in plaintext
    assert "sec_" not in creds[0].primary_secret_hash
    assert creds[0].primary_secret_hash.startswith("scrypt$16384$8$1$")

    # 2. ROTATE
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        rc = cli_main(["rotate", "--client-id", client_id, "--grace-days", "14", "--actor", "ADMIN"], repository=repo)
    assert rc == 0
    output = stdout.getvalue()
    assert "POWER BI MACHINE CREDENTIAL ROTATED" in output
    assert "New Secret:" in output
    assert repo.get_credential_by_client_id(client_id).secondary_secret_hash is not None

    # 3. PROMOTE
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        rc = cli_main(["promote", "--client-id", client_id, "--actor", "ADMIN"], repository=repo)
    assert rc == 0
    output = stdout.getvalue()
    assert "POWER BI MACHINE CREDENTIAL PROMOTED" in output
    assert repo.get_credential_by_client_id(client_id).secondary_secret_hash is None

    # 4. SHOW
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        rc = cli_main(["show", "--client-id", client_id], repository=repo)
    assert rc == 0
    output = stdout.getvalue()
    assert client_id in output
    assert "ACTIVE" in output
    assert "sec_" not in output  # Secrets NEVER printed in show

    # 5. REVOKE
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        rc = cli_main(["revoke", "--client-id", client_id, "--reason", "Decommissioned", "--actor", "ADMIN"], repository=repo)
    assert rc == 0
    output = stdout.getvalue()
    assert "POWER BI MACHINE CREDENTIAL REVOKED" in output
    assert repo.get_credential_by_client_id(client_id).status == "REVOKED"
