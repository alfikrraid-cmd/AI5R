import sys
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parents[1]
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

from ops_common import load_environment, validate_environment


def write_env(tmp_path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text.strip() + "\n", encoding="utf-8")
    return path


def test_validate_environment_accepts_valid_development_configuration(tmp_path):
    env_file = write_env(
        tmp_path,
        """
        AI5R_ENV=development
        AI5R_VERSION=0.1.0
        AI5R_DOMAIN=localhost
        AI5R_PRODUCT_NAME=LTSA-BRAIN
        AI5R_DASHBOARD_PORT=5174
        AI5R_API_PORT=8000
        AI5R_N8N_PORT=5678
        AI5R_MINIO_API_PORT=9000
        AI5R_NGINX_PORT=8080
        AI5R_DASHBOARD_PUBLIC_URL=http://localhost:5174
        AI5R_API_PUBLIC_URL=http://localhost:8000
        AI5R_N8N_PUBLIC_URL=http://localhost:5678
        AI5R_MINIO_PUBLIC_URL=http://127.0.0.1:9000
        AI5R_NGINX_PUBLIC_URL=http://localhost:8080
        AI5R_CORS_ORIGINS=http://localhost:5174,http://127.0.0.1:5174
        AI5R_POSTGRES_IMAGE=postgres:16-alpine
        AI5R_NEO4J_IMAGE=neo4j:5.26-community
        AI5R_REDIS_IMAGE=redis:7.4-alpine
        AI5R_N8N_IMAGE=n8nio/n8n:1.115.3
        AI5R_MINIO_IMAGE=minio/minio:RELEASE.2025-02-28T09-55-16Z
        AI5R_NGINX_IMAGE=nginx:1.27-alpine
        AI5R_GOTENBERG_IMAGE=gotenberg/gotenberg:8
        AI5R_POSTGRES_DB=ai5r_runtime
        AI5R_POSTGRES_USER=ai5r
        AI5R_POSTGRES_PASSWORD=dev-postgres-password
        AI5R_NEO4J_USERNAME=neo4j
        AI5R_NEO4J_PASSWORD=dev-neo4j-password
        AI5R_REDIS_PASSWORD=dev-redis-password
        AI5R_N8N_ENCRYPTION_KEY=dev-n8n-encryption-key-please-change
        AI5R_MINIO_ROOT_USER=ai5rminio
        AI5R_MINIO_ROOT_PASSWORD=dev-minio-password
        """,
    )

    result = validate_environment(load_environment(env_file))

    assert result.ok


def test_validate_environment_accepts_valid_production_like_configuration(tmp_path):
    env_file = write_env(
        tmp_path,
        """
        AI5R_ENV=production
        AI5R_VERSION=1.2.3
        AI5R_DOMAIN=ai5r.example.com
        AI5R_PRODUCT_NAME=LTSA-BRAIN
        AI5R_DASHBOARD_PORT=5174
        AI5R_API_PORT=8000
        AI5R_N8N_PORT=5678
        AI5R_MINIO_API_PORT=9000
        AI5R_NGINX_PORT=8080
        AI5R_DASHBOARD_PUBLIC_URL=https://ai5r.example.com
        AI5R_API_PUBLIC_URL=https://api.ai5r.example.com
        AI5R_N8N_PUBLIC_URL=https://n8n.ai5r.example.com
        AI5R_MINIO_PUBLIC_URL=https://storage.ai5r.example.com
        AI5R_NGINX_PUBLIC_URL=https://ai5r.example.com
        AI5R_CORS_ORIGINS=https://ai5r.example.com
        AI5R_POSTGRES_IMAGE=postgres:16-alpine
        AI5R_NEO4J_IMAGE=neo4j:5.26-community
        AI5R_REDIS_IMAGE=redis:7.4-alpine
        AI5R_N8N_IMAGE=n8nio/n8n:1.115.3
        AI5R_MINIO_IMAGE=minio/minio:RELEASE.2025-02-28T09-55-16Z
        AI5R_NGINX_IMAGE=nginx:1.27-alpine
        AI5R_GOTENBERG_IMAGE=gotenberg/gotenberg:8
        AI5R_POSTGRES_DB=ai5r_runtime
        AI5R_POSTGRES_USER=ai5r
        AI5R_POSTGRES_PASSWORD=prod-postgres-credential
        AI5R_NEO4J_USERNAME=neo4j
        AI5R_NEO4J_PASSWORD=prod-neo4j-credential
        AI5R_REDIS_PASSWORD=prod-redis-credential
        AI5R_N8N_ENCRYPTION_KEY=prod-n8n-encryption-key
        AI5R_MINIO_ROOT_USER=ai5rminio
        AI5R_MINIO_ROOT_PASSWORD=prod-minio-credential
        """,
    )

    result = validate_environment(load_environment(env_file))

    assert result.ok


def test_validate_environment_rejects_missing_required_variable(tmp_path):
    env_file = write_env(
        tmp_path,
        """
        AI5R_ENV=development
        AI5R_VERSION=0.1.0
        AI5R_DOMAIN=localhost
        """,
    )

    result = validate_environment(load_environment(env_file))

    assert not result.ok
    assert "Missing required variable: AI5R_PRODUCT_NAME" in result.errors


def test_validate_environment_rejects_unsafe_production_credential(tmp_path):
    env_file = write_env(
        tmp_path,
        """
        AI5R_ENV=production
        AI5R_VERSION=1.2.3
        AI5R_DOMAIN=ai5r.example.com
        AI5R_PRODUCT_NAME=LTSA-BRAIN
        AI5R_DASHBOARD_PORT=5174
        AI5R_API_PORT=8000
        AI5R_N8N_PORT=5678
        AI5R_MINIO_API_PORT=9000
        AI5R_DASHBOARD_PUBLIC_URL=https://ai5r.example.com
        AI5R_API_PUBLIC_URL=https://api.ai5r.example.com
        AI5R_N8N_PUBLIC_URL=https://n8n.ai5r.example.com
        AI5R_MINIO_PUBLIC_URL=https://storage.ai5r.example.com
        AI5R_CORS_ORIGINS=https://ai5r.example.com
        AI5R_POSTGRES_IMAGE=postgres:16-alpine
        AI5R_NEO4J_IMAGE=neo4j:5.26-community
        AI5R_REDIS_IMAGE=redis:7.4-alpine
        AI5R_N8N_IMAGE=n8nio/n8n:1.115.3
        AI5R_MINIO_IMAGE=minio/minio:RELEASE.2025-02-28T09-55-16Z
        AI5R_POSTGRES_DB=ai5r_runtime
        AI5R_POSTGRES_USER=ai5r
        AI5R_POSTGRES_PASSWORD=change-me
        AI5R_NEO4J_USERNAME=neo4j
        AI5R_NEO4J_PASSWORD=prod-neo4j-credential
        AI5R_REDIS_PASSWORD=prod-redis-credential
        AI5R_N8N_ENCRYPTION_KEY=prod-n8n-encryption-key
        AI5R_MINIO_ROOT_USER=ai5rminio
        AI5R_MINIO_ROOT_PASSWORD=prod-minio-credential
        """,
    )

    result = validate_environment(load_environment(env_file))

    assert not result.ok
    assert any("AI5R_POSTGRES_PASSWORD" in error for error in result.errors)
