from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from backup_restore_common import (
    build_manifest,
    backup_root,
    generate_backup_id,
    prune_expired_backups,
    runtime_volume_names,
    snapshot_configuration,
    write_manifest,
)
from ops_common import DEFAULT_COMPOSE_FILE, DEFAULT_ENV_FILE, compose_command, load_environment, validate_environment

QUIESCED_SERVICES = ("neo4j", "redis", "n8n", "minio")


def run_checked(command: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)
    if completed.returncode != 0:
        output = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(output or f"command failed: {' '.join(command)}")
    return completed


def capture_service_version(env_file: Path, compose_file: Path, service: str, script: str) -> str:
    result = run_checked(compose_command(env_file, compose_file, "exec", "-T", service, "sh", "-lc", script))
    return (result.stdout or result.stderr).strip()


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


def archive_volume(volume_name: str, archive_path: Path, mount_path: str) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
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
            f"cd {mount_path} && tar czf /backup/{archive_path.name} .",
        ]
    )


def backup_postgres(env_file: Path, compose_file: Path, config: dict[str, str], component_dir: Path) -> dict[str, object]:
    component_dir.mkdir(parents=True, exist_ok=True)
    artifact = component_dir / "postgres.dump"
    temp_path = "/tmp/ai5r-postgres.dump"
    run_checked(
        compose_command(
            env_file,
            compose_file,
            "exec",
            "-T",
            "postgres",
            "sh",
            "-lc",
            f'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -C -f {temp_path}',
        )
    )
    run_checked(compose_command(env_file, compose_file, "cp", f"postgres:{temp_path}", str(artifact)))
    run_checked(compose_command(env_file, compose_file, "exec", "-T", "postgres", "rm", "-f", temp_path))
    version = capture_service_version(env_file, compose_file, "postgres", 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -tAc "SELECT version();"')
    return {
        "status": "success",
        "method": "pg_dump custom format with CREATE DATABASE",
        "artifacts": [artifact.relative_to(component_dir.parent.parent).as_posix()],
        "service_version": version,
    }


def export_n8n_workflows(env_file: Path, compose_file: Path, component_dir: Path) -> str:
    workflows_dir = component_dir / "workflows"
    workflows_dir.mkdir(parents=True, exist_ok=True)
    remote_dir = "/tmp/ai5r-n8n-workflows"
    command = compose_command(
        env_file,
        compose_file,
        "exec",
        "-T",
        "n8n",
        "sh",
        "-lc",
        f"rm -rf {remote_dir} && mkdir -p {remote_dir} && n8n export:workflow --all --separate --output={remote_dir}",
    )
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    output = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    if completed.returncode == 0:
        run_checked(compose_command(env_file, compose_file, "cp", f"n8n:{remote_dir}/.", str(workflows_dir)))
    elif "No workflows found with specified filters" in output:
        (workflows_dir / "README.txt").write_text(
            "No workflows were present in the n8n instance at backup time; durable state is preserved by n8n/data.tar.gz.\n",
            encoding="utf-8",
        )
    else:
        raise RuntimeError(output or "n8n workflow export failed")
    subprocess.run(
        compose_command(env_file, compose_file, "exec", "-T", "n8n", "rm", "-rf", remote_dir),
        capture_output=True,
        text=True,
        check=False,
    )
    return workflows_dir.relative_to(component_dir.parent.parent).as_posix()


def backup_runtime_component(
    env_file: Path,
    compose_file: Path,
    component: str,
    archive_name: str,
    volume_name: str,
    mount_path: str,
    component_dir: Path,
) -> dict[str, object]:
    component_dir.mkdir(parents=True, exist_ok=True)
    archive_path = component_dir / archive_name
    archive_volume(volume_name, archive_path, mount_path)
    return {
        "status": "success",
        "method": f"offline tar archive of quiesced volume {volume_name}",
        "artifacts": [archive_path.relative_to(component_dir.parent.parent).as_posix()],
    }


def ensure_stack_accessible(env_file: Path, compose_file: Path) -> None:
    run_checked(compose_command(env_file, compose_file, "ps", "--services"))


def backup_redis_consistency(env_file: Path, compose_file: Path, redis_password: str) -> None:
    run_checked(compose_command(env_file, compose_file, "exec", "-T", "redis", "redis-cli", "-a", redis_password, "BGREWRITEAOF"))
    deadline = time.time() + 60
    while time.time() < deadline:
        result = run_checked(
            compose_command(
                env_file,
                compose_file,
                "exec",
                "-T",
                "redis",
                "redis-cli",
                "-a",
                redis_password,
                "INFO",
                "persistence",
            )
        )
        if "aof_rewrite_in_progress:0" in result.stdout:
            return
        time.sleep(2)
    raise RuntimeError("Timed out waiting for Redis BGREWRITEAOF to complete")


def main() -> int:
    parser = argparse.ArgumentParser(description="Canonical AI5R runtime backup manager")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--compose-file", type=Path, default=DEFAULT_COMPOSE_FILE)
    parser.add_argument("--backup-id", type=str, default=None)
    parser.add_argument("--skip-retention", action="store_true")
    args = parser.parse_args()

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"[FAIL] {error}")
        return 1

    ensure_stack_accessible(args.env_file, args.compose_file)

    root = backup_root(config)
    root.mkdir(parents=True, exist_ok=True)
    backup_id = args.backup_id or generate_backup_id()
    backup_dir = root / backup_id
    backup_dir.mkdir(parents=True, exist_ok=False)
    component_dirs = {name: backup_dir / name for name in ("postgres", "neo4j", "redis", "n8n", "minio")}
    stopped_services: list[str] = []
    components: dict[str, dict[str, object]] = {}

    try:
        config_files = snapshot_configuration(config, args.env_file, args.compose_file, backup_dir)
        components["configuration"] = {
            "status": "success",
            "method": "split portable/secrets env snapshot plus compose metadata",
            "artifacts": [f"configuration/{name}" for name in config_files.values()],
        }

        components["postgres"] = backup_postgres(args.env_file, args.compose_file, config, component_dirs["postgres"])

        workflow_export = export_n8n_workflows(args.env_file, args.compose_file, component_dirs["n8n"])
        backup_redis_consistency(args.env_file, args.compose_file, config["AI5R_REDIS_PASSWORD"])

        for service in QUIESCED_SERVICES:
            run_checked(compose_command(args.env_file, args.compose_file, "stop", service))
            stopped_services.append(service)

        volumes = runtime_volume_names(config)
        components["neo4j"] = backup_runtime_component(
            args.env_file,
            args.compose_file,
            "neo4j",
            "data.tar.gz",
            volumes["neo4j_data"],
            "/data",
            component_dirs["neo4j"],
        )
        archive_volume(volumes["neo4j_logs"], component_dirs["neo4j"] / "logs.tar.gz", "/logs")
        archive_volume(volumes["neo4j_plugins"], component_dirs["neo4j"] / "plugins.tar.gz", "/plugins")
        components["neo4j"]["artifacts"] = [
            "neo4j/data.tar.gz",
            "neo4j/logs.tar.gz",
            "neo4j/plugins.tar.gz",
        ]

        components["redis"] = backup_runtime_component(
            args.env_file,
            args.compose_file,
            "redis",
            "data.tar.gz",
            volumes["redis"],
            "/data",
            component_dirs["redis"],
        )
        components["redis"]["persistence_mode"] = "AOF"

        components["n8n"] = backup_runtime_component(
            args.env_file,
            args.compose_file,
            "n8n",
            "data.tar.gz",
            volumes["n8n"],
            "/data",
            component_dirs["n8n"],
        )
        components["n8n"]["artifacts"] = ["n8n/data.tar.gz", workflow_export]
        components["n8n"]["workflow_export_method"] = "n8n export:workflow --all --separate"

        components["minio"] = backup_runtime_component(
            args.env_file,
            args.compose_file,
            "minio",
            "data.tar.gz",
            volumes["minio"],
            "/data",
            component_dirs["minio"],
        )

        for service in reversed(stopped_services):
            run_checked(compose_command(args.env_file, args.compose_file, "up", "-d", service))
            wait_for_service_health(args.env_file, args.compose_file, service)
        stopped_services.clear()

        manifest = build_manifest(
            backup_id=backup_id,
            config=config,
            env_file=args.env_file,
            compose_file=args.compose_file,
            components=components,
            backup_dir=backup_dir,
            status="success",
            notes=["Plaintext secrets are stored only in configuration/runtime.env.secrets; protect backup storage externally."],
        )
        write_manifest(backup_dir / "manifest.json", manifest)

        removed: list[str] = []
        if not args.skip_retention:
            removed = prune_expired_backups(root, int(config["AI5R_BACKUP_RETENTION_DAYS"]), backup_id)

        print(f"[PASS] backup created: {backup_dir}")
        if removed:
            for name in removed:
                print(f"[PASS] retention removed expired backup: {name}")
        return 0
    except Exception as error:  # noqa: BLE001
        for service in reversed(stopped_services):
            try:
                run_checked(compose_command(args.env_file, args.compose_file, "up", "-d", service))
            except Exception:
                pass
        manifest = build_manifest(
            backup_id=backup_id,
            config=config,
            env_file=args.env_file,
            compose_file=args.compose_file,
            components=components,
            backup_dir=backup_dir,
            status="failed",
            notes=[str(error)],
        )
        write_manifest(backup_dir / "manifest.json", manifest)
        print(f"[FAIL] backup failed: {error}")
        return 1


if __name__ == "__main__":
    sys.exit(main())


