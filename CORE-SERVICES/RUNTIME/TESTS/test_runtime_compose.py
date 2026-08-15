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


# MWO-LTSA-IMPORT-PROD-COMPOSE-ENV-001 -- production acceptance found the api
# container's own OS environment missing AI5R_LTSA_POSTGRES_DB and
# AI5R_IMPORT_ENV_FILE even though the host .env already defines the former
# and dependencies.py reads the latter, because --env-file only makes a var
# available for ${...} interpolation inside compose.yaml itself -- a service
# only receives a var in its own container environment if it is also listed
# under that service's own `environment:` block. These tests guard the two
# concrete symptoms production acceptance observed from regressing again.
def test_api_service_receives_ltsa_postgres_db_and_import_env_file_vars():
    env = parse_env_file(RUNTIME_DIR / ".env.production.example")
    compose = render_compose_with_example_env()
    api_env = compose["services"]["api"]["environment"]

    assert api_env["AI5R_LTSA_POSTGRES_DB"] == env["AI5R_LTSA_POSTGRES_DB"]
    # A fixed, container-internal path -- never the host's own
    # AI5R_IMPORT_ENV_FILE value (an absolute host path, meaningless inside
    # the container's own filesystem namespace).
    assert api_env["AI5R_IMPORT_ENV_FILE"] == "/app/CORE-SERVICES/RUNTIME/.env"


def test_api_service_bind_mounts_the_env_file_at_the_path_it_reports():
    compose = render_compose_with_example_env()
    api = compose["services"]["api"]
    api_env = api["environment"]

    volumes = api.get("volumes") or []
    targets = [v.split(":")[1] for v in volumes if isinstance(v, str) and ":" in v]
    assert api_env["AI5R_IMPORT_ENV_FILE"] in targets
