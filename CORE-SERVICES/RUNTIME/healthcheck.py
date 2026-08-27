from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ops_common import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_ENV_FILE,
    compose_command,
    load_environment,
    run_command,
    validate_environment,
)


EXIT_HEALTHY = 0
EXIT_DEGRADED = 1
EXIT_UNHEALTHY = 2


def http_check(name: str, url: str, timeout: int) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = response.status
    except urllib.error.URLError as error:
        return False, f"{name}: {error}"
    return status == 200, f"{name}: HTTP {status}"


def compose_exec(env_file: Path, compose_file: Path, service: str, script: str) -> tuple[bool, str]:
    command = compose_command(env_file, compose_file, "exec", "-T", service, "sh", "-lc", script)
    completed = run_command(command)
    output = (completed.stdout or completed.stderr).strip()
    return completed.returncode == 0, output or f"{service}: exit {completed.returncode}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Canonical AI5R infrastructure health check. "
            "HEALTHY means every service probe passed. "
            "DEGRADED means dashboard and API passed through nginx but at least one supporting service failed. "
            "UNHEALTHY means the nginx gateway, dashboard route, API route, configuration, "
            "or Docker Compose query failed."
        )
    )
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    args = parser.parse_args()

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"[FAIL] {error}")
        return EXIT_UNHEALTHY

    timeout = int(config.get("AI5R_HEALTH_TIMEOUT_SECONDS", "5"))
    services_result = run_command(compose_command(args.env_file, args.compose_file, "ps", "--services"))
    if services_result.returncode != 0:
        print((services_result.stderr or services_result.stdout).strip())
        return EXIT_UNHEALTHY

    status_lines: list[str] = []
    failures: list[str] = []
    nginx_base_url = config["AI5R_NGINX_PUBLIC_URL"].rstrip("/")

    for ok, message in (
        http_check("nginx", f"{nginx_base_url}/healthz", timeout),
        http_check("nginx->dashboard", nginx_base_url, timeout),
        # MWO-AI5R-WHATSAPP-RUNTIME-OBSERVABILITY-OUTBOUND-025G -- was
        # probing /api/ltsa/pumps, which requires require_permission(
        # "pump.read") (pumps.py) and always returns 401 with no bearer
        # token, producing a false UNHEALTHY. nginx already has a
        # dedicated `location = /health` block (default.conf) whose own
        # comment says it exists so unauthenticated infra checks like
        # this one can reach the API's health JSON -- switching to it,
        # not adding new nginx routing.
        http_check("nginx->api", f"{nginx_base_url}/health", timeout),
        compose_exec(
            args.env_file,
            args.compose_file,
            "n8n",
            "wget -q -O /dev/null http://127.0.0.1:5678/healthz/readiness",
        ),
        http_check("minio", f"{config['AI5R_MINIO_PUBLIC_URL'].rstrip('/')}/minio/health/live", timeout),
        # MWO-AI5R-105 -- gotenberg has no public URL (internal-only, no
        # application caller wired up yet, see compose.yaml's own comment)
        # so it is not probed here; its container-level Docker healthcheck
        # (compose.yaml) already surfaces its status via `docker compose ps`.
        compose_exec(
            args.env_file,
            args.compose_file,
            "postgres",
            'pg_isready -U "$AI5R_POSTGRES_USER" -d "$AI5R_POSTGRES_DB" -h 127.0.0.1',
        ),
        compose_exec(
            args.env_file,
            args.compose_file,
            "neo4j",
            '/var/lib/neo4j/bin/cypher-shell -u "$AI5R_NEO4J_USERNAME" -p "$AI5R_NEO4J_PASSWORD" "RETURN 1;" >/dev/null',
        ),
        compose_exec(
            args.env_file,
            args.compose_file,
            "redis",
            'redis-cli -a "$AI5R_REDIS_PASSWORD" ping | grep PONG >/dev/null',
        ),
    ):
        line = f"[{'PASS' if ok else 'FAIL'}] {message}"
        status_lines.append(line)
        if not ok:
            failures.append(message)

    for line in status_lines:
        print(line)

    critical_failures = [
        failure
        for failure in failures
        if failure.startswith("nginx:")
        or failure.startswith("nginx->dashboard:")
        or failure.startswith("nginx->api:")
    ]

    if not failures:
        print("[HEALTHY] all infrastructure probes passed")
        return EXIT_HEALTHY
    if critical_failures:
        print("[UNHEALTHY] nginx gateway, dashboard route, or api route failed")
        return EXIT_UNHEALTHY

    print("[DEGRADED] nginx, dashboard, and api are up, but one or more supporting services failed")
    return EXIT_DEGRADED


if __name__ == "__main__":
    sys.exit(main())