"""MWO-LTSA-HISTORICAL-JULY-PROMOTION-PREPROD-CLOSURE-001 -- unit coverage
for the historical_pm_cmon_cli.py safety gate and DB-target resolution.
No live Postgres required: `stage`'s "refuse without explicit target"
check runs before any DatabaseRunner is constructed, so it's testable in
isolation (matching this file's own logic order)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import historical_pm_cmon_cli as cli  # noqa: E402


def _args(**overrides):
    class NS:
        pass

    ns = NS()
    ns.pdf = Path("dummy.pdf")
    ns.xlsx = Path("dummy.xlsx")
    ns.area = "HOC"
    ns.env_file = None
    ns.compose_file = None
    ns.database = None
    ns.check_duplicates = False
    ns.yes = False
    ns.pdf_document_id = None
    for k, v in overrides.items():
        setattr(ns, k, v)
    return ns


class TestResolveDatabase:
    def test_explicit_flag_wins(self, monkeypatch):
        monkeypatch.delenv("AI5R_LTSA_POSTGRES_DB", raising=False)
        database, source = cli._resolve_database(_args(database="explicit_db"))
        assert (database, source) == ("explicit_db", "--database")

    def test_env_var_used_when_no_flag(self, monkeypatch):
        monkeypatch.setenv("AI5R_LTSA_POSTGRES_DB", "env_db")
        database, source = cli._resolve_database(_args())
        assert (database, source) == ("env_db", "AI5R_LTSA_POSTGRES_DB")

    def test_default_when_neither_set(self, monkeypatch):
        monkeypatch.delenv("AI5R_LTSA_POSTGRES_DB", raising=False)
        database, source = cli._resolve_database(_args())
        assert source == "default"
        assert database == cli.DatabaseConfig.database  # "ai5r_runtime"


class TestStageRefusesUnconfiguredTarget:
    def test_stage_refuses_and_never_touches_the_database(self, monkeypatch, capsys):
        monkeypatch.delenv("AI5R_LTSA_POSTGRES_DB", raising=False)
        monkeypatch.delenv("AI5R_POSTGRES_HOST", raising=False)

        def _fail_if_called(*a, **k):
            raise AssertionError("DatabaseRunner must never be constructed when the target is unconfigured")

        monkeypatch.setattr(cli, "DatabaseRunner", _fail_if_called)
        exit_code = cli.cmd_stage(_args())
        assert exit_code == 1
        assert "Refusing to stage" in capsys.readouterr().err

    def test_dry_run_has_no_such_refusal(self, monkeypatch):
        # dry-run is zero-write by construction (build_area_dry_run never
        # opens a write transaction) -- it legitimately needs SOME database
        # to read the live pump roster from, so it does not gate on
        # source_kind == "default" the way stage does. Confirmed here by
        # checking cmd_dry_run's own body contains no such early-return.
        import inspect
        assert "Refusing" not in inspect.getsource(cli.cmd_dry_run)


class TestBuildConfigPrefersDirectConnect:
    def test_direct_connect_when_host_env_set(self, monkeypatch):
        monkeypatch.setenv("AI5R_POSTGRES_HOST", "some-host")
        monkeypatch.setenv("AI5R_POSTGRES_PORT", "6543")
        monkeypatch.setenv("AI5R_POSTGRES_USER", "someuser")
        monkeypatch.setenv("AI5R_POSTGRES_PASSWORD", "somepass")
        config = cli._build_config(_args(), "some_db")
        assert config.host == "some-host"
        assert config.port == 6543
        assert config.user == "someuser"
        assert config.database == "some_db"

    def test_docker_exec_mode_when_no_host_env(self, monkeypatch):
        monkeypatch.delenv("AI5R_POSTGRES_HOST", raising=False)
        config = cli._build_config(_args(), "some_db")
        assert config.host is None
        assert config.database == "some_db"


class TestArgparseWiring:
    def test_stage_requires_pdf_xlsx_area(self):
        with pytest.raises(SystemExit):
            cli.main(["stage"])

    def test_dry_run_has_no_yes_flag(self):
        # --yes only makes sense for stage (the only writing subcommand).
        with pytest.raises(SystemExit):
            cli.main(["dry-run", "--pdf", "a.pdf", "--xlsx", "a.xlsx", "--area", "HOC", "--yes"])
