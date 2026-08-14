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
