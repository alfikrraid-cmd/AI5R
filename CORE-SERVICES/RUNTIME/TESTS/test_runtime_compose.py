import re
import sys
from pathlib import Path

import yaml

RUNTIME_DIR = Path(__file__).resolve().parents[1]
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from ops_common import parse_env_file


def render_compose_with_example_env(env_file: Path | None = None) -> dict:
    compose_text = (RUNTIME_DIR / "compose.yaml").read_text(encoding="utf-8-sig")
    env = parse_env_file(env_file or (RUNTIME_DIR / ".env.production.example"))

    def replace_var(match: re.Match[str]) -> str:
        key = match.group(1)
        assert key in env, f"Missing compose variable in example env: {key}"
        return env[key]

    rendered = re.sub(r"\$\{([A-Z0-9_]+)\}", replace_var, compose_text)
    return yaml.safe_load(rendered)


def test_rendered_production_compose_wires_n8n_internal_persistence_to_runtime_postgres():
    compose = render_compose_with_example_env()
    n8n = compose["services"]["n8n"]
    postgres_env = compose["services"]["postgres"]["environment"]
    n8n_env = n8n["environment"]

    assert postgres_env["POSTGRES_DB"] == "ai5r_runtime"
    assert n8n_env["DB_TYPE"] == "postgresdb"
    assert n8n_env["DB_POSTGRESDB_HOST"] == "postgres"
    assert n8n_env["DB_POSTGRESDB_PORT"] == 5432
    assert n8n_env["DB_POSTGRESDB_DATABASE"] == "ai5r_runtime"
    assert n8n_env["DB_POSTGRESDB_USER"] == "ai5r"
    assert n8n_env["DB_POSTGRESDB_PASSWORD"] == "REPLACE_WITH_PRODUCTION_POSTGRES_PASSWORD_32_CHARS_MIN"


def test_rendered_production_compose_prevents_n8n_sqlite_fallback():
    compose = render_compose_with_example_env()
    n8n_env = compose["services"]["n8n"]["environment"]

    assert n8n_env.get("DB_TYPE") == "postgresdb"
    assert all(key in n8n_env for key in (
        "DB_POSTGRESDB_HOST",
        "DB_POSTGRESDB_PORT",
        "DB_POSTGRESDB_DATABASE",
        "DB_POSTGRESDB_USER",
        "DB_POSTGRESDB_PASSWORD",
    ))
    assert not any(key.startswith("DB_SQLITE") for key in n8n_env)


def test_n8n_waits_for_postgres_health_before_starting():
    compose = render_compose_with_example_env()

    assert compose["services"]["n8n"]["depends_on"] == {
        "postgres": {"condition": "service_healthy"}
    }


def test_runtime_and_ltsa_database_targets_remain_separate():
    env = parse_env_file(RUNTIME_DIR / ".env.production.example")
    compose = render_compose_with_example_env()
    n8n_env = compose["services"]["n8n"]["environment"]

    assert env["AI5R_POSTGRES_DB"] == "ai5r_runtime"
    assert env["AI5R_LTSA_POSTGRES_DB"] == "ltsa_brain"
    assert n8n_env["DB_POSTGRESDB_DATABASE"] == env["AI5R_POSTGRES_DB"]
    assert n8n_env["DB_POSTGRESDB_DATABASE"] != env["AI5R_LTSA_POSTGRES_DB"]


# MWO-LTSA-IMPORT-DIRECT-DB-001 -- the api container has neither the
# docker CLI nor a mounted docker.sock, so `docker compose exec postgres
# psql` (the previous mechanism) is structurally unusable there no matter
# how its env vars are wired. Import now connects to Postgres directly
# (psycopg2, over the backend network) -- the same DB_POSTGRESDB_HOST
# pattern n8n already uses (reused below via api_env["AI5R_POSTGRES_HOST"]
# == n8n_env["DB_POSTGRESDB_HOST"]), and the same credentials n8n's own
# DB_POSTGRESDB_USER/PASSWORD/PORT already read (reused, never a second
# secret). This test guards the concrete wiring production acceptance
# needs from regressing.
def test_api_service_connects_directly_to_postgres_reusing_n8n_credentials():
    compose = render_compose_with_example_env()
    api_env = compose["services"]["api"]["environment"]
    n8n_env = compose["services"]["n8n"]["environment"]

    assert api_env["AI5R_POSTGRES_HOST"] == n8n_env["DB_POSTGRESDB_HOST"] == "postgres"
    assert api_env["AI5R_POSTGRES_PORT"] == n8n_env["DB_POSTGRESDB_PORT"]
    assert api_env["AI5R_POSTGRES_USER"] == n8n_env["DB_POSTGRESDB_USER"]
    assert api_env["AI5R_POSTGRES_PASSWORD"] == n8n_env["DB_POSTGRESDB_PASSWORD"]
    # Still the LTSA-canonical database -- direct-connect mode targets the
    # same database docker-exec mode did (only the mechanism changed).
    assert api_env["AI5R_LTSA_POSTGRES_DB"] == "ltsa_brain"


def test_api_service_no_longer_bind_mounts_env_file_or_sets_import_env_file():
    # MWO-LTSA-IMPORT-PROD-COMPOSE-ENV-001's bind-mount + AI5R_IMPORT_ENV_FILE
    # design (docker-exec mode's own env-file plumbing) is obsolete now that
    # direct-connect mode reads credentials from real container env vars,
    # never a mounted file -- this guards against that obsolete infrastructure
    # being reintroduced/stacked alongside the new mechanism.
    compose = render_compose_with_example_env()
    api = compose["services"]["api"]

    assert "AI5R_IMPORT_ENV_FILE" not in api["environment"]
    assert not api.get("volumes")
