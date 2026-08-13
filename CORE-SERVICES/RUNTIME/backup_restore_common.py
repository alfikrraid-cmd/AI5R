from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from ops_common import RUNTIME_DIR, SECRET_VARS

BACKUP_PREFIX = "ai5r-backup-"
REQUIRED_COMPONENTS = ("postgres", "neo4j", "redis", "n8n", "minio", "configuration")
IMAGE_KEYS = (
    "AI5R_POSTGRES_IMAGE",
    "AI5R_NEO4J_IMAGE",
    "AI5R_REDIS_IMAGE",
    "AI5R_N8N_IMAGE",
    "AI5R_MINIO_IMAGE",
    "AI5R_DASHBOARD_IMAGE_REPO",
    "AI5R_API_IMAGE_REPO",
)


@dataclass(slots=True)
class BackupValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def generate_backup_id(now: datetime | None = None) -> str:
    current = now or utc_now()
    return f"{BACKUP_PREFIX}{current.strftime('%Y%m%dT%H%M%SZ')}"


def backup_root(config: dict[str, str]) -> Path:
    raw = config.get("AI5R_BACKUP_ROOT", "./BACKUPS")
    path = Path(raw)
    if not path.is_absolute():
        path = (RUNTIME_DIR / path).resolve()
    return path


def runtime_volume_names(config: dict[str, str]) -> dict[str, str]:
    prefix = config["AI5R_VOLUME_PREFIX"]
    return {
        "postgres": f"{prefix}-postgres-data",
        "neo4j_data": f"{prefix}-neo4j-data",
        "neo4j_logs": f"{prefix}-neo4j-logs",
        "neo4j_plugins": f"{prefix}-neo4j-plugins",
        "redis": f"{prefix}-redis-data",
        "n8n": f"{prefix}-n8n-data",
        "minio": f"{prefix}-minio-data",
    }


def runtime_identity(config: dict[str, str]) -> dict[str, str]:
    return {
        "product_name": config.get("AI5R_PRODUCT_NAME", ""),
        "ai5r_version": config.get("AI5R_VERSION", ""),
        "ai5r_env": config.get("AI5R_ENV", ""),
        "compose_project": config.get("AI5R_COMPOSE_PROJECT", ""),
        "volume_prefix": config.get("AI5R_VOLUME_PREFIX", ""),
    }


def redact_environment(config: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    public: dict[str, str] = {}
    secrets: dict[str, str] = {}
    for key in sorted(config):
        if not key.startswith("AI5R_"):
            continue
        value = config[key]
        if key in SECRET_VARS:
            secrets[key] = value
        else:
            public[key] = value
    return public, secrets


def write_env_snapshot(path: Path, values: dict[str, str]) -> None:
    lines = [f"{key}={values[key]}" for key in sorted(values)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def snapshot_configuration(
    config: dict[str, str],
    env_file: Path,
    compose_file: Path,
    destination: Path,
) -> dict[str, str]:
    config_dir = destination / "configuration"
    config_dir.mkdir(parents=True, exist_ok=True)

    public_env, secret_env = redact_environment(config)
    public_env_path = config_dir / "runtime.env.public"
    secret_env_path = config_dir / "runtime.env.secrets"
    compose_copy_path = config_dir / "compose.yaml"
    metadata_path = config_dir / "runtime-metadata.json"

    write_env_snapshot(public_env_path, public_env)
    write_env_snapshot(secret_env_path, secret_env)
    shutil.copy2(compose_file, compose_copy_path)

    metadata = {
        "source_env_file": str(env_file),
        "source_compose_file": str(compose_file),
        "runtime_identity": runtime_identity(config),
        "image_configuration": {key: config[key] for key in IMAGE_KEYS if key in config},
        "secret_keys": sorted(secret_env),
        "created_at": utc_now().isoformat().replace("+00:00", "Z"),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "public_env": public_env_path.name,
        "secret_env": secret_env_path.name,
        "compose": compose_copy_path.name,
        "metadata": metadata_path.name,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_inventory(backup_dir: Path) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path in sorted(p for p in backup_dir.rglob("*") if p.is_file() and p.name != "manifest.json"):
        artifacts.append(
            {
                "relative_path": path.relative_to(backup_dir).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    return artifacts


def build_manifest(
    *,
    backup_id: str,
    config: dict[str, str],
    env_file: Path,
    compose_file: Path,
    components: dict[str, dict[str, Any]],
    backup_dir: Path,
    status: str,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "backup_id": backup_id,
        "created_at": utc_now().isoformat().replace("+00:00", "Z"),
        "status": status,
        "ai5r_version": config.get("AI5R_VERSION", ""),
        "ai5r_env": config.get("AI5R_ENV", ""),
        "runtime_identity": runtime_identity(config),
        "source_env_file": str(env_file),
        "source_compose_file": str(compose_file),
        "components": components,
        "secret_keys": sorted(SECRET_VARS),
        "artifacts": artifact_inventory(backup_dir),
        "notes": notes or [],
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def backup_dir_from_ref(config: dict[str, str], backup_ref: str) -> Path:
    candidate = Path(backup_ref)
    if candidate.exists():
        return candidate.resolve()
    return (backup_root(config) / backup_ref).resolve()


def validate_backup_set(backup_dir: Path) -> BackupValidationResult:
    result = BackupValidationResult()
    manifest_path = backup_dir / "manifest.json"
    if not backup_dir.exists():
        result.errors.append(f"Backup directory does not exist: {backup_dir}")
        return result
    if not manifest_path.exists():
        result.errors.append(f"Missing manifest: {manifest_path}")
        return result

    try:
        manifest = load_manifest(manifest_path)
    except json.JSONDecodeError as error:
        result.errors.append(f"Malformed manifest JSON: {error}")
        return result

    if manifest.get("status") != "success":
        result.errors.append(f"Backup manifest is not successful: status={manifest.get('status')}")

    components = manifest.get("components", {})
    for component in REQUIRED_COMPONENTS:
        if component not in components:
            result.errors.append(f"Missing component entry in manifest: {component}")
            continue
        component_status = components[component].get("status")
        if component_status != "success":
            result.errors.append(f"Component {component} not successful in manifest: {component_status}")

    artifacts = manifest.get("artifacts", [])
    if not artifacts:
        result.errors.append("Manifest has no artifact inventory")
        return result

    for artifact in artifacts:
        rel_path = artifact.get("relative_path")
        if not rel_path:
            result.errors.append("Artifact entry missing relative_path")
            continue
        path = backup_dir / rel_path
        if not path.exists():
            result.errors.append(f"Missing artifact: {rel_path}")
            continue
        size_bytes = path.stat().st_size
        if size_bytes != artifact.get("size_bytes"):
            result.errors.append(f"Artifact size mismatch: {rel_path}")
        checksum = sha256_file(path)
        if checksum != artifact.get("sha256"):
            result.errors.append(f"Artifact checksum mismatch: {rel_path}")

    return result


def is_recognized_backup_dir(path: Path) -> bool:
    return path.is_dir() and path.name.startswith(BACKUP_PREFIX) and (path / "manifest.json").exists()


def list_backup_dirs(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if is_recognized_backup_dir(path))


def _parse_manifest_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def prune_expired_backups(root: Path, retention_days: int, keep_backup_id: str) -> list[str]:
    cutoff = utc_now() - timedelta(days=retention_days)
    removed: list[str] = []

    for backup_dir in list_backup_dirs(root):
        if backup_dir.name == keep_backup_id:
            continue
        manifest = load_manifest(backup_dir / "manifest.json")
        created_at = _parse_manifest_datetime(manifest.get("created_at", ""))
        if created_at is None:
            continue
        if created_at >= cutoff:
            continue
        shutil.rmtree(backup_dir)
        removed.append(backup_dir.name)

    return removed


def restore_configuration_artifacts(backup_dir: Path, target_dir: Path) -> list[str]:
    config_dir = backup_dir / "configuration"
    target_dir.mkdir(parents=True, exist_ok=True)
    restored: list[str] = []
    for name in ("runtime.env.public", "runtime.env.secrets", "compose.yaml", "runtime-metadata.json"):
        source = config_dir / name
        if not source.exists():
            continue
        destination = target_dir / name
        shutil.copy2(source, destination)
        restored.append(destination.name)
    return restored

