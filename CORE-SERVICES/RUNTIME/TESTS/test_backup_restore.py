import json
import sys
from datetime import datetime, timezone
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parents[1]
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from backup_restore_common import (  # noqa: E402
    BackupValidationResult,
    build_manifest,
    generate_backup_id,
    prune_expired_backups,
    snapshot_configuration,
    validate_backup_set,
    write_manifest,
)


BASE_CONFIG = {
    "AI5R_ENV": "development",
    "AI5R_VERSION": "0.1.0",
    "AI5R_DOMAIN": "localhost",
    "AI5R_PRODUCT_NAME": "LTSA-BRAIN",
    "AI5R_COMPOSE_PROJECT": "ai5r-runtime-verify",
    "AI5R_VOLUME_PREFIX": "ai5r-runtime-verify",
    "AI5R_BACKUP_ROOT": "./BACKUPS",
    "AI5R_BACKUP_RETENTION_DAYS": "14",
    "AI5R_POSTGRES_IMAGE": "postgres:16-alpine",
    "AI5R_NEO4J_IMAGE": "neo4j:5.26-community",
    "AI5R_REDIS_IMAGE": "redis:7.4-alpine",
    "AI5R_N8N_IMAGE": "n8nio/n8n:1.115.3",
    "AI5R_MINIO_IMAGE": "minio/minio:RELEASE.2025-02-28T09-55-16Z",
    "AI5R_DASHBOARD_IMAGE_REPO": "ai5r/dashboard",
    "AI5R_API_IMAGE_REPO": "ai5r/api",
    "AI5R_POSTGRES_PASSWORD": "dev-postgres-password",
    "AI5R_NEO4J_PASSWORD": "dev-neo4j-password",
    "AI5R_REDIS_PASSWORD": "dev-redis-password",
    "AI5R_N8N_ENCRYPTION_KEY": "dev-n8n-encryption-key-please-change",
    "AI5R_MINIO_ROOT_PASSWORD": "dev-minio-password",
}


def make_backup_tree(tmp_path: Path) -> Path:
    backup_dir = tmp_path / "ai5r-backup-20260809T120000Z"
    for component in ("postgres", "neo4j", "redis", "n8n", "minio", "configuration"):
        (backup_dir / component).mkdir(parents=True, exist_ok=True)
    (backup_dir / "postgres" / "postgres.dump").write_text("postgres", encoding="utf-8")
    (backup_dir / "neo4j" / "data.tar.gz").write_text("neo4j-data", encoding="utf-8")
    (backup_dir / "neo4j" / "logs.tar.gz").write_text("neo4j-logs", encoding="utf-8")
    (backup_dir / "neo4j" / "plugins.tar.gz").write_text("neo4j-plugins", encoding="utf-8")
    (backup_dir / "redis" / "data.tar.gz").write_text("redis", encoding="utf-8")
    (backup_dir / "n8n" / "data.tar.gz").write_text("n8n", encoding="utf-8")
    (backup_dir / "minio" / "data.tar.gz").write_text("minio", encoding="utf-8")
    (backup_dir / "configuration" / "runtime.env.public").write_text("AI5R_ENV=development\n", encoding="utf-8")
    (backup_dir / "configuration" / "runtime.env.secrets").write_text("AI5R_POSTGRES_PASSWORD=secret\n", encoding="utf-8")
    (backup_dir / "configuration" / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
    (backup_dir / "configuration" / "runtime-metadata.json").write_text("{}\n", encoding="utf-8")
    return backup_dir


def test_generate_backup_id_uses_canonical_format():
    backup_id = generate_backup_id(datetime(2026, 8, 9, 12, 34, 56, tzinfo=timezone.utc))
    assert backup_id == "ai5r-backup-20260809T123456Z"


def test_snapshot_configuration_splits_public_and_secret_values(tmp_path):
    env_file = tmp_path / ".env"
    compose_file = tmp_path / "compose.yaml"
    env_file.write_text("AI5R_ENV=development\n", encoding="utf-8")
    compose_file.write_text("services: {}\n", encoding="utf-8")

    snapshot_configuration(BASE_CONFIG, env_file, compose_file, tmp_path)

    public_env = (tmp_path / "configuration" / "runtime.env.public").read_text(encoding="utf-8")
    secret_env = (tmp_path / "configuration" / "runtime.env.secrets").read_text(encoding="utf-8")
    metadata = json.loads((tmp_path / "configuration" / "runtime-metadata.json").read_text(encoding="utf-8"))

    assert "AI5R_POSTGRES_PASSWORD" not in public_env
    assert "AI5R_POSTGRES_PASSWORD=dev-postgres-password" in secret_env
    assert "AI5R_POSTGRES_PASSWORD" in metadata["secret_keys"]


def test_validate_backup_set_rejects_missing_artifact(tmp_path):
    backup_dir = make_backup_tree(tmp_path)
    manifest = build_manifest(
        backup_id=backup_dir.name,
        config=BASE_CONFIG,
        env_file=tmp_path / ".env",
        compose_file=tmp_path / "compose.yaml",
        components={component: {"status": "success"} for component in ("postgres", "neo4j", "redis", "n8n", "minio", "configuration")},
        backup_dir=backup_dir,
        status="success",
    )
    write_manifest(backup_dir / "manifest.json", manifest)
    (backup_dir / "redis" / "data.tar.gz").unlink()

    result = validate_backup_set(backup_dir)

    assert not result.ok
    assert "Missing artifact: redis/data.tar.gz" in result.errors


def test_validate_backup_set_rejects_corrupt_checksum(tmp_path):
    backup_dir = make_backup_tree(tmp_path)
    manifest = build_manifest(
        backup_id=backup_dir.name,
        config=BASE_CONFIG,
        env_file=tmp_path / ".env",
        compose_file=tmp_path / "compose.yaml",
        components={component: {"status": "success"} for component in ("postgres", "neo4j", "redis", "n8n", "minio", "configuration")},
        backup_dir=backup_dir,
        status="success",
    )
    write_manifest(backup_dir / "manifest.json", manifest)
    (backup_dir / "postgres" / "postgres.dump").write_text("tampered", encoding="utf-8")

    result = validate_backup_set(backup_dir)

    assert not result.ok
    assert "Artifact checksum mismatch: postgres/postgres.dump" in result.errors


def test_validate_backup_set_requires_success_manifest(tmp_path):
    backup_dir = make_backup_tree(tmp_path)
    manifest = build_manifest(
        backup_id=backup_dir.name,
        config=BASE_CONFIG,
        env_file=tmp_path / ".env",
        compose_file=tmp_path / "compose.yaml",
        components={component: {"status": "success"} for component in ("postgres", "neo4j", "redis", "n8n", "minio", "configuration")},
        backup_dir=backup_dir,
        status="failed",
    )
    write_manifest(backup_dir / "manifest.json", manifest)

    result = validate_backup_set(backup_dir)

    assert not result.ok
    assert "Backup manifest is not successful: status=failed" in result.errors


def test_prune_expired_backups_only_removes_recognized_old_sets(tmp_path):
    keep_dir = make_backup_tree(tmp_path)
    old_dir = tmp_path / "ai5r-backup-20260801T000000Z"
    old_dir.mkdir()
    write_manifest(
        old_dir / "manifest.json",
        {
            "backup_id": old_dir.name,
            "created_at": "2026-08-01T00:00:00Z",
            "status": "success",
            "components": {},
            "artifacts": [{"relative_path": "dummy.txt", "size_bytes": 1, "sha256": "x"}],
        },
    )
    (old_dir / "dummy.txt").write_text("x", encoding="utf-8")
    stray = tmp_path / "not-a-backup"
    stray.mkdir()

    removed = prune_expired_backups(tmp_path, retention_days=3, keep_backup_id=keep_dir.name)

    assert old_dir.name in removed
    assert not old_dir.exists()
    assert keep_dir.exists()
    assert stray.exists()
