from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from ltsa_internal_component_upsert import plan_internal_component_import


def parse_shaft_size(value: Any) -> float | None:
    if value is None:
        return None

    text = str(value).strip().upper().replace(" ", "")
    if not text:
        return None

    if text.endswith('"'):
        text = text[:-1]

    if text.endswith("MM"):
        text = text[:-2]

    if "." in text and "/" in text:
        whole, fraction = text.split(".", 1)
        try:
            return float(int(whole) + Fraction(fraction))
        except (ValueError, ZeroDivisionError):
            return None

    if "/" in text:
        try:
            return float(Fraction(text))
        except (ValueError, ZeroDivisionError):
            return None

    try:
        return float(text)
    except ValueError:
        return None


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text or None


def _same_number(left: float | None, right: float | None) -> bool:
    if left is None and right is None:
        return True
    if left is None or right is None:
        return False
    return abs(left - right) < 1e-9


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _is_placeholder_pump_tag(value: Any) -> bool:
    normalized = (_normalize_text(value) or '').casefold()
    return normalized in {'-', 'n/a', 'belum diketahui', 'unknown'}


def _json_query(sql: str, runner: "DatabaseRunner") -> list[dict[str, Any]]:
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(t))::text, '[]') FROM ({sql}) t;"
    raw = runner.query_scalar(wrapped)
    return json.loads(raw or "[]")


@dataclass
class DatabaseConfig:
    # docker-exec mode (CLI/dev only -- unchanged from before
    # MWO-LTSA-IMPORT-DIRECT-DB-001): host machine has the `docker` CLI and
    # shells out to `docker compose exec postgres psql`. Required for this
    # mode, unused (may be left None) for direct-connect mode below.
    env_file: Path | None = None
    compose_file: Path | None = None
    service: str = "postgres"
    user: str = "ai5r"
    database: str = "ai5r_runtime"
    # Direct-connect mode (MWO-LTSA-IMPORT-DIRECT-DB-001) -- a real wire-
    # protocol Postgres connection via psycopg2, no docker CLI/socket
    # required. Selected whenever `host` is set (see DatabaseRunner below).
    # This is the mode the production api container uses: it has neither
    # the docker CLI nor a mounted docker.sock (MWO-LTSA-IMPORT-PROD-
    # COMPOSE-ENV-001's own disclosed blocker), so docker-exec mode is
    # structurally unusable there.
    host: str | None = None
    port: int = 5432
    password: str | None = None


class DatabaseRunner:
    """Same public interface (`query_scalar`/`execute_script`) regardless
    of mode -- every existing caller (import_execution_engine.py,
    import_session_repository.py, import_adapter.py, the ingestion CLIs,
    ...) is unmodified by MWO-LTSA-IMPORT-DIRECT-DB-001; only how a
    DatabaseConfig is CONSTRUCTED differs by caller (see dependencies.py's
    own _resolve_import_database_config for the production/API choice)."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    def _base_command(self) -> list[str]:
        return [
            "docker",
            "compose",
            "--env-file",
            str(self.config.env_file),
            "-f",
            str(self.config.compose_file),
            "exec",
            "-T",
            self.config.service,
            "psql",
            "-U",
            self.config.user,
            "-d",
            self.config.database,
            "-v",
            "ON_ERROR_STOP=1",
        ]

    def _direct_connect(self):
        # Deferred import: a CLI/dev caller that never sets config.host
        # never imports psycopg2 at all -- no new dependency burden for
        # that path (requirements.txt still gains psycopg2-binary for the
        # api container's own venv, but nothing forces it onto a bare
        # host running the ingestion CLI directly).
        import psycopg2

        conn = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.user,
            password=self.config.password,
            dbname=self.config.database,
        )
        # autocommit=True: every execute_script() script below already
        # carries its own literal BEGIN;...COMMIT; (apply_plan(),
        # execute_import()) -- exactly mirroring psql's own behavior
        # (psql forwards the script to the server verbatim; the script's
        # own BEGIN/COMMIT is what actually controls the transaction).
        # Leaving psycopg2's default (autocommit=False) would make
        # psycopg2 ALSO wrap every execute() in its own implicit
        # transaction, nesting a second BEGIN inside the script's own --
        # harmless per Postgres (a warning, not an error) but needless.
        # Under Postgres's simple-query protocol, a mid-script error
        # aborts the transaction and skips every statement after it
        # (including the trailing COMMIT;) -- the same
        # "-v ON_ERROR_STOP=1, nothing after the failure runs" semantics
        # psql already provides. Each call opens and closes its own
        # connection (no pooling) -- this mirrors the existing docker-exec
        # mode exactly (a fresh psql process per call), keeping "one
        # script, one atomic outcome" true in both modes.
        conn.autocommit = True
        return conn

    def query_scalar(self, sql: str) -> str:
        if self.config.host:
            conn = self._direct_connect()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
                    row = cursor.fetchone()
                    if row is None or row[0] is None:
                        return ""
                    return str(row[0])
            finally:
                conn.close()

        result = subprocess.run(
            self._base_command() + ["-tAc", sql],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def execute_script(self, sql: str) -> None:
        if self.config.host:
            conn = self._direct_connect()
            try:
                with conn.cursor() as cursor:
                    cursor.execute(sql)
            finally:
                conn.close()
            return

        subprocess.run(
            self._base_command(),
            check=True,
            input=sql,
            text=True,
            capture_output=True,
        )


def load_state(runner: DatabaseRunner) -> dict[str, list[dict[str, Any]]]:
    return {
        "pumps": _json_query(
            "SELECT tag_number, area, location, pump_type, api_plan, seal_type, status, "
            "manufacturer, model, drawing_ref, notes, name, criticality FROM ltsa_pumps",
            runner,
        ),
        "seals": _json_query(
            "SELECT seal_code, seal_name, manufacturer, model, shaft_size, material, "
            "temperature_limit, pressure_limit, status FROM seal_registry",
            runner,
        ),
        "stock": _json_query(
            "SELECT seal_code, quantity_on_hand, reorder_point, location FROM seal_stock",
            runner,
        ),
        "compatibility": _json_query(
            "SELECT seal_code, pump_tag_number, notes FROM seal_pump_compatibility",
            runner,
        ),
        "internal_components": _json_query(
            "SELECT component_id, component_class, gpn_number, gpn_status, identity_fingerprint, "
            "description, size_text, specification, source_workbook_name, source_sheet_name, "
            "source_row_number, remarks FROM internal_component_master",
            runner,
        ),
        "internal_component_stock": _json_query(
            "SELECT component_stock_id, component_id, quantity_on_hand, warehouse_name, rack_name, "
            "location_tag, source_workbook_name, source_sheet_name, source_row_number, remarks "
            "FROM internal_component_stock",
            runner,
        ),
        "seal_internal_component_link": _json_query(
            "SELECT seal_code, component_id, relationship_basis, source_workbook_name, "
            "source_sheet_name, source_row_number FROM seal_internal_component_link",
            runner,
        ),
    }


def reconcile_seals(
    projected_seals: list[dict[str, Any]],
    existing_seals: list[dict[str, Any]],
) -> tuple[dict[str, str], dict[str, int], list[dict[str, Any]]]:
    exact_by_code = {row["seal_code"]: row for row in existing_seals}
    exact_by_identity: defaultdict[tuple[str | None, float | None], list[dict[str, Any]]] = defaultdict(list)
    name_index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in existing_seals:
        identity = (_normalize_text(row.get("seal_name")), _to_float(row.get("shaft_size")))
        exact_by_identity[identity].append(row)
        if _normalize_text(row.get("seal_name")) is not None:
            name_index[_normalize_text(row.get("seal_name"))].append(row)

    seal_code_map: dict[str, str] = {}
    counts = Counter()
    issues: list[dict[str, Any]] = []
    claimed_new_codes: set[str] = set()

    for seal in projected_seals:
        projected_code = seal["seal_code"]
        seal_name = _normalize_text(seal.get("seal_name"))
        shaft_size = parse_shaft_size(seal.get("shaft_size"))
        identity = (seal_name, shaft_size)

        exact_code = exact_by_code.get(projected_code)
        if exact_code is not None:
            exact_code_identity = (
                _normalize_text(exact_code.get("seal_name")),
                _to_float(exact_code.get("shaft_size")),
            )
            if exact_code_identity == identity or (
                exact_code_identity[0] == seal_name and exact_code_identity[1] is None
            ):
                counts["exact_existing_match"] += 1
                seal_code_map[projected_code] = projected_code
                continue

            counts["conflict"] += 1
            issues.append(
                {
                    "classification": "conflict",
                    "projected_seal_code": projected_code,
                    "reason": "projected seal_code collides with different canonical identity",
                    "projected_identity": {"seal_name": seal_name, "shaft_size": shaft_size},
                    "existing_identity": {
                        "seal_name": _normalize_text(exact_code.get("seal_name")),
                        "shaft_size": _to_float(exact_code.get("shaft_size")),
                    },
                }
            )
            continue

        exact_identity_rows = exact_by_identity.get(identity, [])
        if len(exact_identity_rows) == 1:
            counts["exact_existing_match"] += 1
            seal_code_map[projected_code] = exact_identity_rows[0]["seal_code"]
            continue

        if len(exact_identity_rows) > 1:
            counts["ambiguous"] += 1
            issues.append(
                {
                    "classification": "ambiguous",
                    "projected_seal_code": projected_code,
                    "reason": "multiple canonical seals match the same identity",
                    "projected_identity": {"seal_name": seal_name, "shaft_size": shaft_size},
                    "existing_seal_codes": [row["seal_code"] for row in exact_identity_rows],
                }
            )
            continue

        name_matches = name_index.get(seal_name or "", [])
        if shaft_size is None and name_matches:
            counts["ambiguous"] += 1
            issues.append(
                {
                    "classification": "ambiguous",
                    "projected_seal_code": projected_code,
                    "reason": "seal_name exists canonically but shaft_size is absent or unparseable",
                    "projected_identity": {"seal_name": seal_name, "shaft_size": shaft_size},
                    "existing_seal_codes": [row["seal_code"] for row in name_matches],
                }
            )
            continue

        if projected_code in claimed_new_codes:
            counts["conflict"] += 1
            issues.append(
                {
                    "classification": "conflict",
                    "projected_seal_code": projected_code,
                    "reason": "duplicate projected deterministic seal_code",
                }
            )
            continue

        claimed_new_codes.add(projected_code)
        counts["safe_new"] += 1
        seal_code_map[projected_code] = projected_code

    return seal_code_map, dict(counts), issues


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def plan_import(projection: dict[str, Any], state: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    seal_code_map, seal_counts, seal_issues = reconcile_seals(
        projection["seal_registry"],
        state["seals"],
    )

    existing_pumps = {row["tag_number"]: row for row in state["pumps"]}
    existing_seals = {row["seal_code"]: row for row in state["seals"]}
    existing_stock = {row["seal_code"]: row for row in state["stock"]}
    existing_compatibility = {
        (row["seal_code"], row["pump_tag_number"]): row for row in state["compatibility"]
    }

    plan = {
        "conflicts": list(seal_issues),
        "ambiguous_records": [issue for issue in seal_issues if issue["classification"] == "ambiguous"],
        "rejected_records": [issue for issue in seal_issues if issue["classification"] == "conflict"],
        "resolved_seal_code_map": seal_code_map,
        "seal_identity_reconciliation": {
            "exact_existing_match": seal_counts.get("exact_existing_match", 0),
            "safe_new": seal_counts.get("safe_new", 0),
            "ambiguous": seal_counts.get("ambiguous", 0),
            "conflict": seal_counts.get("conflict", 0),
        },
        "pumps": {"insert": [], "update": [], "unchanged": [], "rejected": []},
        "seals": {"insert": [], "update": [], "unchanged": [], "rejected": []},
        "stock": {"insert": [], "update": [], "unchanged": [], "rejected": []},
        "compatibility": {"insert": [], "update": [], "unchanged": [], "rejected": []},
    }

    unresolved_codes = {
        issue["projected_seal_code"]
        for issue in seal_issues
        if issue.get("projected_seal_code") is not None
    }

    for projected in projection["ltsa_pumps"]:
        if _is_placeholder_pump_tag(projected.get("tag_number")):
            issue = {
                "classification": "conflict",
                "projected_pump_tag": projected.get("tag_number"),
                "reason": "placeholder pump tag cannot be imported into canonical pump registry",
            }
            plan["conflicts"].append(issue)
            plan["rejected_records"].append(issue)
            plan["pumps"]["rejected"].append(projected.get("tag_number"))
            continue

        payload = {
            "tag_number": projected["tag_number"],
            "area": _normalize_text(projected.get("area")),
            "pump_type": _normalize_text(projected.get("pump_type")),
            "seal_type": _normalize_text(projected.get("seal_type")),
            "drawing_ref": _normalize_text(projected.get("drawing_ref")),
        }
        existing = existing_pumps.get(projected["tag_number"])
        if existing is None:
            plan["pumps"]["insert"].append(payload)
            continue

        updates = _merge_fields(
            existing,
            payload,
            replace_fields={"area", "pump_type", "seal_type", "drawing_ref"},
        )
        if updates:
            plan["pumps"]["update"].append({"tag_number": projected["tag_number"], "fields": updates})
        else:
            plan["pumps"]["unchanged"].append(projected["tag_number"])

    for projected in projection["seal_registry"]:
        if projected["seal_code"] in unresolved_codes:
            plan["seals"]["rejected"].append(projected["seal_code"])
            continue

        resolved_code = seal_code_map[projected["seal_code"]]
        payload = {
            "seal_code": resolved_code,
            "seal_name": _normalize_text(projected.get("seal_name")),
            # Inference from schema vs workbook: shaft_size is NUMERIC canonically,
            # so workbook strings are normalized to a numeric value where parseable.
            "shaft_size": parse_shaft_size(projected.get("shaft_size")),
            "manufacturer": "John Crane",
        }
        existing = existing_seals.get(resolved_code)
        if existing is None:
            plan["seals"]["insert"].append(payload)
            continue

        updates = _merge_fields(existing, payload, replace_fields=set())
        if updates:
            plan["seals"]["update"].append({"seal_code": resolved_code, "fields": updates})
        else:
            plan["seals"]["unchanged"].append(resolved_code)

    for projected in projection["seal_stock"]:
        if projected["seal_code"] in unresolved_codes:
            plan["stock"]["rejected"].append(projected["seal_code"])
            continue

        resolved_code = seal_code_map[projected["seal_code"]]
        payload = {
            "seal_code": resolved_code,
            "quantity_on_hand": projected.get("quantity_on_hand"),
            # reorder_point in the projection is inferred, not workbook-native.
            "reorder_point": None,
            "location": _normalize_text(projected.get("location")),
        }
        existing = existing_stock.get(resolved_code)
        if existing is None:
            plan["stock"]["insert"].append(payload)
            continue

        updates = _merge_fields(
            existing,
            payload,
            replace_fields={"quantity_on_hand", "location"},
        )
        updates.pop("reorder_point", None)
        if updates:
            plan["stock"]["update"].append({"seal_code": resolved_code, "fields": updates})
        else:
            plan["stock"]["unchanged"].append(resolved_code)

    known_pump_tags = set(existing_pumps) | {row["tag_number"] for row in plan["pumps"]["insert"]} | set(plan["pumps"]["unchanged"])

    for projected in projection["seal_pump_compatibility"]:
        if projected["seal_code"] in unresolved_codes:
            plan["compatibility"]["rejected"].append(
                f"{projected['seal_code']}::{projected['pump_tag_number']}"
            )
            continue

        if _is_placeholder_pump_tag(projected.get("pump_tag_number")) or projected.get("pump_tag_number") not in known_pump_tags:
            issue = {
                "classification": "conflict",
                "projected_seal_code": projected.get("seal_code"),
                "projected_pump_tag": projected.get("pump_tag_number"),
                "reason": "compatibility references a pump tag that is not safely resolvable canonically",
            }
            plan["conflicts"].append(issue)
            plan["rejected_records"].append(issue)
            plan["compatibility"]["rejected"].append(
                f"{projected['seal_code']}::{projected['pump_tag_number']}"
            )
            continue

        resolved_code = seal_code_map[projected["seal_code"]]
        key = (resolved_code, projected["pump_tag_number"])
        payload = {
            "seal_code": resolved_code,
            "pump_tag_number": projected["pump_tag_number"],
            "notes": _normalize_text(projected.get("notes")),
        }
        existing = existing_compatibility.get(key)
        if existing is None:
            plan["compatibility"]["insert"].append(payload)
            continue

        updates = _merge_fields(existing, payload, replace_fields=set())
        if updates:
            plan["compatibility"]["update"].append(
                {"seal_code": resolved_code, "pump_tag_number": projected["pump_tag_number"], "fields": updates}
            )
        else:
            plan["compatibility"]["unchanged"].append(f"{resolved_code}::{projected['pump_tag_number']}")

    component_plan, component_conflicts, resolved_component_ids = plan_internal_component_import(
        projection,
        state,
        normalize_text=_normalize_text,
        is_blank=_is_blank,
    )
    plan.update(component_plan)
    plan["conflicts"].extend(component_conflicts)
    plan["resolved_component_id_map"] = resolved_component_ids
    plan["dry_run"] = summarize_plan(plan)
    return plan


def _merge_fields(
    existing: dict[str, Any],
    incoming: dict[str, Any],
    *,
    replace_fields: set[str],
) -> dict[str, Any]:
    updates: dict[str, Any] = {}
    for key, new_value in incoming.items():
        if key not in existing:
            continue

        old_value = existing.get(key)
        if key == "shaft_size":
            if old_value is None and new_value is not None:
                updates[key] = new_value
            continue

        if _is_blank(new_value):
            continue

        if key in replace_fields:
            if str(old_value) != str(new_value):
                updates[key] = new_value
            continue

        if _is_blank(old_value):
            updates[key] = new_value
    return updates


def summarize_plan(plan: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {
        entity: {
            "insert": len(plan[entity]["insert"]),
            "update": len(plan[entity]["update"]),
            "unchanged": len(plan[entity]["unchanged"]),
            "rejected": len(plan[entity]["rejected"]),
        }
        for entity in ("pumps", "seals", "stock", "compatibility", "internal_components", "internal_component_stock", "seal_internal_component_link")
    }


def apply_plan(plan: dict[str, Any], runner: DatabaseRunner) -> dict[str, Any]:
    reconciliation = plan.get("seal_identity_reconciliation", {})
    if reconciliation.get("ambiguous", 0) or reconciliation.get("conflict", 0):
        raise RuntimeError("Refusing to apply import with unresolved canonical seal identity conflicts")

    statements = ["BEGIN;"]
    for pump in plan["pumps"]["insert"]:
        statements.append(
            "INSERT INTO ltsa_pumps (tag_number, area, pump_type, seal_type, drawing_ref) VALUES "
            f"({_sql(pump['tag_number'])}, {_sql(pump['area'])}, {_sql(pump['pump_type'])}, "
            f"{_sql(pump['seal_type'])}, {_sql(pump['drawing_ref'])});"
        )
    for update in plan["pumps"]["update"]:
        statements.append(_build_update("ltsa_pumps", "tag_number", update["tag_number"], update["fields"]))

    for seal in plan["seals"]["insert"]:
        statements.append(
            "INSERT INTO seal_registry (seal_code, seal_name, manufacturer, shaft_size) VALUES "
            f"({_sql(seal['seal_code'])}, {_sql(seal['seal_name'])}, {_sql(seal['manufacturer'])}, "
            f"{_sql(seal['shaft_size'])});"
        )
    for update in plan["seals"]["update"]:
        statements.append(_build_update("seal_registry", "seal_code", update["seal_code"], update["fields"]))

    for stock in plan["stock"]["insert"]:
        statements.append(
            "INSERT INTO seal_stock (seal_code, quantity_on_hand, reorder_point, location) VALUES "
            f"({_sql(stock['seal_code'])}, {_sql(stock['quantity_on_hand'])}, {_sql(stock['reorder_point'])}, "
            f"{_sql(stock['location'])});"
        )
    for update in plan["stock"]["update"]:
        statements.append(_build_update("seal_stock", "seal_code", update["seal_code"], update["fields"]))

    for compatibility in plan["compatibility"]["insert"]:
        statements.append(
            "INSERT INTO seal_pump_compatibility (seal_code, pump_tag_number, notes) VALUES "
            f"({_sql(compatibility['seal_code'])}, {_sql(compatibility['pump_tag_number'])}, {_sql(compatibility['notes'])});"
        )
    for update in plan["compatibility"]["update"]:
        where = (
            "WHERE seal_code = "
            f"{_sql(update['seal_code'])} AND pump_tag_number = {_sql(update['pump_tag_number'])}"
        )
        assignments = ", ".join(f"{column} = {_sql(value)}" for column, value in sorted(update["fields"].items()))
        statements.append(f"UPDATE seal_pump_compatibility SET {assignments} {where};")

    for component in plan.get("internal_components", {}).get("insert", []):
        statements.append(
            "INSERT INTO internal_component_master (component_id, component_class, gpn_number, gpn_status, "
            "identity_fingerprint, description, size_text, specification, source_workbook_name, "
            "source_sheet_name, source_row_number, remarks) VALUES "
            f"({_sql(component['component_id'])}, {_sql(component['component_class'])}, {_sql(component['gpn_number'])}, "
            f"{_sql(component['gpn_status'])}, {_sql(component['identity_fingerprint'])}, {_sql(component['description'])}, "
            f"{_sql(component['size_text'])}, {_sql(component['specification'])}, {_sql(component['source_workbook_name'])}, "
            f"{_sql(component['source_sheet_name'])}, {_sql(component['source_row_number'])}, {_sql(component['remarks'])});"
        )
    for update in plan.get("internal_components", {}).get("update", []):
        statements.append(_build_update("internal_component_master", "component_id", update["component_id"], update["fields"]))

    for stock in plan.get("internal_component_stock", {}).get("insert", []):
        statements.append(
            "INSERT INTO internal_component_stock (component_stock_id, component_id, quantity_on_hand, warehouse_name, "
            "rack_name, location_tag, source_workbook_name, source_sheet_name, source_row_number, remarks) VALUES "
            f"({_sql(stock['component_stock_id'])}, {_sql(stock['component_id'])}, {_sql(stock['quantity_on_hand'])}, "
            f"{_sql(stock['warehouse_name'])}, {_sql(stock['rack_name'])}, {_sql(stock['location_tag'])}, "
            f"{_sql(stock['source_workbook_name'])}, {_sql(stock['source_sheet_name'])}, {_sql(stock['source_row_number'])}, {_sql(stock['remarks'])});"
        )
    for update in plan.get("internal_component_stock", {}).get("update", []):
        statements.append(_build_update("internal_component_stock", "component_stock_id", update["component_stock_id"], update["fields"]))

    for link in plan.get("seal_internal_component_link", {}).get("insert", []):
        statements.append(
            "INSERT INTO seal_internal_component_link (seal_code, component_id, relationship_basis, source_workbook_name, source_sheet_name, source_row_number) VALUES "
            f"({_sql(link['seal_code'])}, {_sql(link['component_id'])}, {_sql(link['relationship_basis'])}, {_sql(link['source_workbook_name'])}, {_sql(link['source_sheet_name'])}, {_sql(link['source_row_number'])});"
        )

    statements.append("COMMIT;")
    runner.execute_script("\n".join(statements))
    return summarize_plan(plan)


def _build_update(table: str, key_column: str, key_value: Any, fields: dict[str, Any]) -> str:
    assignments = ", ".join(f"{column} = {_sql(value)}" for column, value in sorted(fields.items()))
    return f"UPDATE {table} SET {assignments}, updated_at = NOW() WHERE {key_column} = {_sql(key_value)};"


def _sql(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def bootstrap_schema(runner: DatabaseRunner, schema_file: Path) -> None:
    runner.execute_script(schema_file.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Dry-run and apply LTSA projection into canonical Postgres")
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--compose-file", type=Path, required=True)
    parser.add_argument("--schema-file", type=Path, required=True)
    parser.add_argument("--mode", choices=("dry-run", "apply"), default="dry-run")
    parser.add_argument("--bootstrap-schema", action="store_true")
    # MWO-LTSA-DB-UPSERT-TARGET-001 -- this CLI never passed `database=` to
    # DatabaseConfig, so it always silently fell back to the dataclass's
    # own default ("ai5r_runtime") regardless of which database the caller
    # actually meant -- ltsa_bootstrap_admin.py and BACKEND-API/
    # dependencies.py already resolve the real LTSA database the same way
    # (AI5R_LTSA_POSTGRES_DB, defaulting to "ai5r_runtime"); this CLI now
    # follows that same existing convention, with an explicit --database
    # flag layered on top for zero-ambiguity production invocations.
    parser.add_argument(
        "--database",
        default=None,
        help="Target Postgres database. Defaults to AI5R_LTSA_POSTGRES_DB "
        "if set, else 'ai5r_runtime' (DatabaseConfig's own default).",
    )
    args = parser.parse_args()

    env_database = os.getenv("AI5R_LTSA_POSTGRES_DB")
    database = args.database or env_database or DatabaseConfig.database
    database_source = "--database" if args.database else ("AI5R_LTSA_POSTGRES_DB" if env_database else "default")

    # Apply is the one mode that writes. Refusing to apply against the bare,
    # unconfigured fallback (neither an explicit --database nor the
    # canonical env var was actually supplied) is the "must not accidentally
    # write to ai5r_runtime" property this MWO requires, without demanding
    # --database on every single invocation (the canonical env var alone,
    # already correctly set in every real .env file, remains sufficient).
    if args.mode == "apply" and database_source == "default":
        print(
            "Refusing to apply with no explicit database target: pass --database "
            "or set AI5R_LTSA_POSTGRES_DB. (Currently would default to "
            f"'{database}', which is almost never the intended LTSA database.)",
            file=sys.stderr,
        )
        return 1

    # Fail-safe observability (never logs credentials) -- the resolved
    # target must be visible before any read/write happens.
    print(f"Target database: {database} (source: {database_source})", file=sys.stderr)

    projection = json.loads(args.projection.read_text(encoding="utf-8"))
    runner = DatabaseRunner(DatabaseConfig(env_file=args.env_file, compose_file=args.compose_file, database=database))

    if args.bootstrap_schema:
        bootstrap_schema(runner, args.schema_file)

    state = load_state(runner)
    plan = plan_import(projection, state)
    result: dict[str, Any] = {"plan": plan}

    if args.mode == "apply":
        result["applied"] = apply_plan(plan, runner)
        result["post_apply_counts"] = {
            "ltsa_pumps": runner.query_scalar("SELECT count(*) FROM ltsa_pumps"),
            "seal_registry": runner.query_scalar("SELECT count(*) FROM seal_registry"),
            "seal_stock": runner.query_scalar("SELECT count(*) FROM seal_stock"),
            "seal_pump_compatibility": runner.query_scalar("SELECT count(*) FROM seal_pump_compatibility"),
            "internal_component_master": runner.query_scalar("SELECT count(*) FROM internal_component_master"),
            "internal_component_stock": runner.query_scalar("SELECT count(*) FROM internal_component_stock"),
            "seal_internal_component_link": runner.query_scalar("SELECT count(*) FROM seal_internal_component_link"),
        }

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
