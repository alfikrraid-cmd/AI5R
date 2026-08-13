from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

from backup_restore_common import (
    backup_dir_from_ref,
    restore_configuration_artifacts,
    runtime_volume_names,
    validate_backup_set,
)
from ops_common import DEFAULT_COMPOSE_FILE, DEFAULT_ENV_FILE, compose_command, load_environment, validate_environment


def run_checked(command: list[str]) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        output = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(output or f"command failed: {' '.join(command)}")
    return completed


def service_container_id(env_file: Path, compose_file: Path, service: str) -> str:
    result = run_checked(compose_command(env_file, compose_file, "ps", "-q", service))
    container_id = result.stdout.strip()
    if not container_id:
        raise RuntimeError(f"No container id found for service: {service}")
    return container_id


def wait_for_service_health(env_file: Path, compose_file: Path, service: str, timeout_seconds: int = 180) -> None:
    deadline = time.time() + timeout_seconds
    container_id = service_container_id(env_file, compose_file, service)
    while time.time() < deadline:
        inspect = run_checked(
            [
                "docker",
                "inspect",
                "--format",
                "{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}",
                container_id,
            ]
        )
        status = inspect.stdout.strip()
        if status == "healthy":
            return
        if status in {"exited", "dead"}:
            raise RuntimeError(f"Service {service} is not running: {status}")
        time.sleep(3)
    raise RuntimeError(f"Timed out waiting for service {service} to become healthy")


def ensure_volume_removed(name: str) -> None:
    subprocess.run(["docker", "volume", "rm", "-f", name], capture_output=True, text=True, check=False)


def ensure_volume_created(name: str) -> None:
    run_checked(["docker", "volume", "create", name])


def extract_volume(volume_name: str, archive_path: Path, mount_path: str) -> None:
    run_checked(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{volume_name}:{mount_path}",
            "-v",
            f"{archive_path.parent.resolve()}:/backup",
            "alpine",
            "sh",
            "-lc",
            f"find {mount_path} -mindepth 1 -delete && tar xzf /backup/{archive_path.name} -C {mount_path}",
        ]
    )


def copy_into_container(env_file: Path, compose_file: Path, service: str, source: Path, destination: str) -> None:
    run_checked(compose_command(env_file, compose_file, "cp", str(source), f"{service}:{destination}"))


def restore_postgres(env_file: Path, compose_file: Path, backup_dir: Path) -> None:
    artifact = backup_dir / "postgres" / "postgres.dump"
    run_checked(compose_command(env_file, compose_file, "up", "-d", "postgres"))
    wait_for_service_health(env_file, compose_file, "postgres")
    copy_into_container(env_file, compose_file, "postgres", artifact, "/tmp/restore-postgres.dump")
    run_checked(
        compose_command(
            env_file,
            compose_file,
            "exec",
            "-T",
            "postgres",
            "sh",
            "-lc",
            'pg_restore -U "$POSTGRES_USER" -C -d postgres --clean --if-exists /tmp/restore-postgres.dump',
        )
    )
    run_checked(compose_command(env_file, compose_file, "exec", "-T", "postgres", "rm", "-f", "/tmp/restore-postgres.dump"))


def run_healthcheck(env_file: Path, compose_file: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).with_name("healthcheck.py")),
            "--env-file",
            str(env_file),
            "--compose-file",
            str(compose_file),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout, end="")
    if result.returncode != 0:
        raise RuntimeError("Canonical healthcheck failed after restore")


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical AI5R runtime restore manager")
    parser.add_argument("backup_ref", type=str, help="Backup ID or explicit backup directory path")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--yes", action="store_true", help="Confirm destructive restore")
    parser.add_argument("--restore-config-dir", type=Path, default=None)
    parser.add_argument("--allow-version-mismatch", action="store_true")
    args = parser.parse_args()

    if not args.yes:
        print("[FAIL] restore requires --yes to confirm destructive operations")
        return 1

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"[FAIL] {error}")
        return 1

    backup_dir = backup_dir_from_ref(config, args.backup_ref)
    backup_validation = validate_backup_set(backup_dir)
    if not backup_validation.ok:
        for error in backup_validation.errors:
            print(f"[FAIL] {error}")
        return 1

    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    if not args.allow_version_mismatch:
        if manifest.get("ai5r_version") != config.get("AI5R_VERSION"):
            print("[FAIL] backup AI5R_VERSION does not match current runtime configuration")
            return 1
        if manifest.get("ai5r_env") != config.get("AI5R_ENV"):
            print("[FAIL] backup AI5R_ENV does not match current runtime configuration")
            return 1

    restore_config_dir = args.restore_config_dir or (Path(__file__).resolve().parent / "RESTORED-CONFIG" / manifest["backup_id"])
    restored_config = restore_configuration_artifacts(backup_dir, restore_config_dir)
    if restored_config:
        print(f"[PASS] configuration artifacts restored to {restore_config_dir}")

    run_checked(compose_command(args.env_file, args.compose_file, "down"))

    volumes = runtime_volume_names(config)
    for name in volumes.values():
        ensure_volume_removed(name)
        ensure_volume_created(name)

    extract_volume(volumes["neo4j_data"], backup_dir / "neo4j" / "data.tar.gz", "/data")
    extract_volume(volumes["neo4j_logs"], backup_dir / "neo4j" / "logs.tar.gz", "/logs")
    extract_volume(volumes["neo4j_plugins"], backup_dir / "neo4j" / "plugins.tar.gz", "/plugins")
    extract_volume(volumes["redis"], backup_dir / "redis" / "data.tar.gz", "/data")
    extract_volume(volumes["n8n"], backup_dir / "n8n" / "data.tar.gz", "/data")
    extract_volume(volumes["minio"], backup_dir / "minio" / "data.tar.gz", "/data")

    restore_postgres(args.env_file, args.compose_file, backup_dir)

    run_checked(compose_command(args.env_file, args.compose_file, "up", "-d"))
    for service in ("postgres", "neo4j", "redis", "n8n", "minio", "api", "dashboard"):
        wait_for_service_health(args.env_file, args.compose_file, service)

    run_healthcheck(args.env_file, args.compose_file)
    print(f"[PASS] restore completed: {backup_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

