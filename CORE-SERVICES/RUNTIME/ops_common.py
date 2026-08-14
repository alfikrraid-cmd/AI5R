from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent
DEFAULT_ENV_FILE = RUNTIME_DIR / ".env"
DEFAULT_COMPOSE_FILE = RUNTIME_DIR / "compose.yaml"

SUPPORTED_ENVS = {"development", "staging", "production", "onprem"}
PRODUCTION_LIKE_ENVS = {"staging", "production", "onprem"}

REQUIRED_VARS = (
    "AI5R_ENV",
    "AI5R_VERSION",
    "AI5R_DOMAIN",
    "AI5R_PRODUCT_NAME",
    "AI5R_DASHBOARD_PORT",
    "AI5R_API_PORT",
    "AI5R_N8N_PORT",
    "AI5R_MINIO_API_PORT",
    "AI5R_NGINX_PORT",
    "AI5R_DASHBOARD_PUBLIC_URL",
    "AI5R_API_PUBLIC_URL",
    "AI5R_N8N_PUBLIC_URL",
    "AI5R_MINIO_PUBLIC_URL",
    "AI5R_NGINX_PUBLIC_URL",
    "AI5R_CORS_ORIGINS",
    "AI5R_POSTGRES_IMAGE",
    "AI5R_NEO4J_IMAGE",
    "AI5R_REDIS_IMAGE",
    "AI5R_N8N_IMAGE",
    "AI5R_MINIO_IMAGE",
    "AI5R_NGINX_IMAGE",
    "AI5R_GOTENBERG_IMAGE",
    "AI5R_POSTGRES_DB",
    "AI5R_LTSA_POSTGRES_DB",
    "AI5R_POSTGRES_USER",
    "AI5R_POSTGRES_PASSWORD",
    "AI5R_NEO4J_USERNAME",
    "AI5R_NEO4J_PASSWORD",
    "AI5R_REDIS_PASSWORD",
    "AI5R_N8N_ENCRYPTION_KEY",
    "AI5R_MINIO_ROOT_USER",
    "AI5R_MINIO_ROOT_PASSWORD",
)

PORT_VARS = (
    "AI5R_DASHBOARD_PORT",
    "AI5R_API_PORT",
    "AI5R_N8N_PORT",
    "AI5R_MINIO_API_PORT",
    "AI5R_NGINX_PORT",
)

SECRET_VARS = (
    "AI5R_POSTGRES_PASSWORD",
    "AI5R_NEO4J_PASSWORD",
    "AI5R_REDIS_PASSWORD",
    "AI5R_N8N_ENCRYPTION_KEY",
    "AI5R_MINIO_ROOT_PASSWORD",
)

UNSAFE_SECRET_VALUES = {
    "",
    "changeme",
    "change-me",
    "password",
    "default",
    "admin",
    "dev-postgres-password",
    "dev-neo4j-password",
    "dev-redis-password",
    "dev-n8n-encryption-key-please-change",
    "dev-minio-password",
}


@dataclass(slots=True)
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_environment(env_file: Path | None = None) -> dict[str, str]:
    env_path = env_file or DEFAULT_ENV_FILE
    config = parse_env_file(env_path)
    for key, value in os.environ.items():
        if key.startswith("AI5R_"):
            config[key] = value
    return config


def validate_environment(config: dict[str, str]) -> ValidationResult:
    result = ValidationResult()

    for key in REQUIRED_VARS:
        if not config.get(key):
            result.errors.append(f"Missing required variable: {key}")

    ai5r_env = config.get("AI5R_ENV", "")
    if ai5r_env and ai5r_env not in SUPPORTED_ENVS:
        result.errors.append(
            f"Unsupported AI5R_ENV '{ai5r_env}'. Supported values: {', '.join(sorted(SUPPORTED_ENVS))}"
        )

    for key in PORT_VARS:
        value = config.get(key)
        if not value:
            continue
        try:
            port = int(value)
        except ValueError:
            result.errors.append(f"Invalid port for {key}: {value}")
            continue
        if port < 1 or port > 65535:
            result.errors.append(f"Port out of range for {key}: {port}")

    for key in (
        "AI5R_DASHBOARD_PUBLIC_URL",
        "AI5R_API_PUBLIC_URL",
        "AI5R_N8N_PUBLIC_URL",
        "AI5R_MINIO_PUBLIC_URL",
        "AI5R_NGINX_PUBLIC_URL",
    ):
        value = config.get(key, "")
        if value and not value.startswith(("http://", "https://")):
            result.errors.append(f"{key} must start with http:// or https://")

    if ai5r_env in PRODUCTION_LIKE_ENVS:
        domain = config.get("AI5R_DOMAIN", "")
        if domain in {"localhost", "127.0.0.1"}:
            result.errors.append("Production-like environments must not use localhost as AI5R_DOMAIN")

        for key in SECRET_VARS:
            if config.get(key, "").strip().lower() in UNSAFE_SECRET_VALUES:
                result.errors.append(
                    f"Unsafe default credential for production-like environment: {key}"
                )

    if config.get("AI5R_N8N_IMAGE", "").endswith(":latest"):
        result.errors.append("AI5R_N8N_IMAGE must be pinned and must not use :latest")

    if config.get("AI5R_DOMAIN", "").startswith("http://") or config.get("AI5R_DOMAIN", "").startswith("https://"):
        result.errors.append("AI5R_DOMAIN must be a host/domain only, not a URL")

    if config.get("AI5R_BACKUP_RETENTION_DAYS"):
        try:
            retention = int(config["AI5R_BACKUP_RETENTION_DAYS"])
        except ValueError:
            result.errors.append("AI5R_BACKUP_RETENTION_DAYS must be an integer")
        else:
            if retention < 1:
                result.errors.append("AI5R_BACKUP_RETENTION_DAYS must be >= 1")

    return result


def compose_command(
    env_file: Path | None = None,
    compose_file: Path | None = None,
    *args: str,
) -> list[str]:
    return [
        "docker",
        "compose",
        "--env-file",
        str(env_file or DEFAULT_ENV_FILE),
        "-f",
        str(compose_file or DEFAULT_COMPOSE_FILE),
        *args,
    ]


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, check=False)

