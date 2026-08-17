"""MWO-LTSA-DB-UPSERT-TARGET-001 -- proves ltsa_pump_inventory_db_upsert.py's
main() resolves an explicit database target (never silently defaulting to
"ai5r_runtime" for a real LTSA run), using the exact AI5R_LTSA_POSTGRES_DB
convention ltsa_bootstrap_admin.py/BACKEND-API/dependencies.py already
establish. A dedicated file rather than editing the existing (untracked,
pre-existing) test_ltsa_pump_inventory_db_upsert.py, which has no main()/CLI
coverage at all today.
"""

import json
import subprocess
import sys
from pathlib import Path

INGESTION_DIR = Path(__file__).resolve().parents[1]
SCRIPT = INGESTION_DIR / "ltsa_pump_inventory_db_upsert.py"


def _run(args, env_overrides=None, env_unset=()):
    import os

    env = dict(os.environ)
    for key in env_unset:
        env.pop(key, None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )


def _empty_projection(tmp_path):
    path = tmp_path / "projection.json"
    path.write_text(
        json.dumps({"ltsa_pumps": [], "seal_registry": [], "seal_stock": [], "seal_pump_compatibility": []}),
        encoding="utf-8",
    )
    return path


def _base_args(tmp_path, mode="dry-run"):
    return [
        "--projection",
        str(_empty_projection(tmp_path)),
        "--env-file",
        str(tmp_path / "does-not-need-to-exist.env"),
        "--compose-file",
        str(tmp_path / "does-not-need-to-exist-compose.yaml"),
        "--schema-file",
        str(tmp_path / "does-not-need-to-exist-schema.sql"),
        "--mode",
        mode,
    ]


def test_help_exposes_database_option():
    result = _run(["--help"])
    assert "--database" in result.stdout


def test_explicit_database_flag_is_resolved_and_reported(tmp_path):
    result = _run(_base_args(tmp_path) + ["--database", "ltsa_brain"], env_unset=("AI5R_LTSA_POSTGRES_DB",))
    assert "Target database: ltsa_brain (source: --database)" in result.stderr


def test_env_var_is_resolved_and_reported_when_no_explicit_flag(tmp_path):
    result = _run(_base_args(tmp_path), env_overrides={"AI5R_LTSA_POSTGRES_DB": "ltsa_brain"})
    assert "Target database: ltsa_brain (source: AI5R_LTSA_POSTGRES_DB)" in result.stderr


def test_explicit_flag_wins_over_env_var(tmp_path):
    result = _run(
        _base_args(tmp_path) + ["--database", "ltsa_brain"],
        env_overrides={"AI5R_LTSA_POSTGRES_DB": "some-other-db"},
    )
    assert "Target database: ltsa_brain (source: --database)" in result.stderr


def test_dry_run_with_neither_explicit_flag_nor_env_var_still_uses_the_unchanged_default(tmp_path):
    # dry-run is read-only-in-intent and pre-existing callers may rely on
    # the historical default -- only apply is hard-blocked (Rule: "must
    # not accidentally WRITE to ai5r_runtime").
    result = _run(_base_args(tmp_path), env_unset=("AI5R_LTSA_POSTGRES_DB",))
    assert "Target database: ai5r_runtime (source: default)" in result.stderr


def test_apply_refuses_with_no_explicit_or_canonical_database_selection(tmp_path):
    result = _run(_base_args(tmp_path, mode="apply"), env_unset=("AI5R_LTSA_POSTGRES_DB",))
    assert result.returncode == 1
    assert "Refusing to apply with no explicit database target" in result.stderr


def test_apply_proceeds_past_the_guard_with_explicit_database_flag(tmp_path):
    result = _run(_base_args(tmp_path, mode="apply") + ["--database", "ltsa_brain"], env_unset=("AI5R_LTSA_POSTGRES_DB",))
    # Never reaches a real Postgres in this test (no live DB) -- proves the
    # guard did NOT block it, i.e. it got past the "Refusing to apply"
    # check and printed the resolved target before attempting to connect.
    assert "Refusing to apply" not in result.stderr
    assert "Target database: ltsa_brain (source: --database)" in result.stderr


def test_apply_proceeds_past_the_guard_with_canonical_env_var(tmp_path):
    result = _run(_base_args(tmp_path, mode="apply"), env_overrides={"AI5R_LTSA_POSTGRES_DB": "ltsa_brain"})
    assert "Refusing to apply" not in result.stderr
    assert "Target database: ltsa_brain (source: AI5R_LTSA_POSTGRES_DB)" in result.stderr


def test_target_database_output_never_contains_a_password(tmp_path):
    # Fail-safe observability requirement: the resolved-target line must
    # never leak credentials, even when a real-looking password is present
    # in the process environment at the same time.
    result = _run(
        _base_args(tmp_path) + ["--database", "ltsa_brain"],
        env_overrides={"AI5R_POSTGRES_PASSWORD": "super-secret-value-must-not-leak"},
    )
    assert "super-secret-value-must-not-leak" not in result.stdout
    assert "super-secret-value-must-not-leak" not in result.stderr
