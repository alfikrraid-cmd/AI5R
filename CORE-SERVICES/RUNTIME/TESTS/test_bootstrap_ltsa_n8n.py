import sys
from pathlib import Path

import pytest

RUNTIME_DIR = Path(__file__).resolve().parents[1]
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from bootstrap_ltsa_n8n import get_or_create_postgres_credential


class FakeN8nClient:
    def __init__(self, credentials=None):
        self.credentials = credentials if credentials is not None else []
        self.created_payload = None

    def request(self, path, *, method="GET", payload=None, authenticated=True):
        if path == "/rest/credentials" and method == "GET":
            return 200, {}, self.credentials
        if path == "/rest/credentials" and method == "POST":
            self.created_payload = payload
            return 200, {}, {"id": "cred-ltsa", "name": payload["name"]}
        raise AssertionError(f"unexpected request: {method} {path}")


def credential_env(**overrides):
    env = {
        "AI5R_POSTGRES_DB": "ai5r_runtime",
        "AI5R_LTSA_POSTGRES_DB": "ltsa_brain",
        "AI5R_POSTGRES_USER": "ai5r",
        "AI5R_POSTGRES_PASSWORD": "postgres-secret",
        "AI5R_POSTGRES_PORT": "15432",
    }
    env.update(overrides)
    return env


def test_ltsa_postgres_credential_targets_ltsa_database_and_preserves_connection_settings():
    client = FakeN8nClient()
    env = credential_env()

    result = get_or_create_postgres_credential(client, env)

    assert result == {"id": "cred-ltsa", "name": "Postgres account", "created": True}
    assert env["AI5R_POSTGRES_DB"] == "ai5r_runtime"
    assert client.created_payload["data"] == {
        "host": "postgres",
        "database": "ltsa_brain",
        "user": "ai5r",
        "password": "postgres-secret",
        "port": 15432,
        "maxConnections": 100,
        "allowUnauthorizedCerts": False,
        "ssl": "disable",
    }


def test_existing_postgres_credential_is_reused_without_changing_bootstrap_scope():
    client = FakeN8nClient(
        credentials=[{"id": "existing", "name": "Postgres account", "type": "postgres"}]
    )

    result = get_or_create_postgres_credential(client, credential_env())

    assert result == {"id": "existing", "name": "Postgres account", "created": False}
    assert client.created_payload is None


def test_missing_ltsa_database_configuration_fails_clearly():
    client = FakeN8nClient()
    env = credential_env(AI5R_LTSA_POSTGRES_DB="")

    with pytest.raises(RuntimeError, match="AI5R_LTSA_POSTGRES_DB"):
        get_or_create_postgres_credential(client, env)
