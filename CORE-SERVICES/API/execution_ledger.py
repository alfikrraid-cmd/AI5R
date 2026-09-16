from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

# Bounds (protection against unbounded blob growth)
MAX_PAYLOAD_BYTES = 256 * 1024  # 256 KB
MAX_DIFF_BYTES = 64 * 1024      # 64 KB (matches sandbox max diff)
MAX_SUMMARY_BYTES = 16 * 1024   # 16 KB
MAX_ERROR_BYTES = 8 * 1024      # 8 KB

SCHEMA_VERSION = 1


def _now() -> str:
    return datetime.now(UTC).isoformat()


class LedgerError(Exception):
    """Base exception for execution ledger operations."""
    pass


class LedgerPersistenceError(LedgerError):
    """Raised when an atomic write or transaction to the ledger fails."""
    pass


class LedgerCorruptionError(LedgerError):
    """Raised when the database schema or data format is invalid/corrupt."""
    pass


class LedgerBoundExceededError(LedgerError):
    """Raised when payload, diff, or summary exceeds safety bounds."""
    pass


class ExecutionLedger:
    """Canonical durable execution ledger for AI5R Digital Workforce.

    Provides persistent, restart-safe provenance for missions, execution plans,
    work items, executions, artifacts, test results, and Chief approvals.
    Uses standard-library sqlite3 with WAL mode, foreign keys, and strict bounds.
    """

    def __init__(self, db_path: str | Path | None = None) -> None:
        if db_path is None:
            env_path = os.environ.get("AI5R_EXECUTION_LEDGER_PATH")
            if env_path:
                self.db_path = Path(env_path).resolve()
            else:
                default_dir = Path(__file__).resolve().parent.parent / "DATA"
                default_dir.mkdir(parents=True, exist_ok=True)
                self.db_path = default_dir / "execution_ledger.db"
        elif str(db_path) == ":memory:":
            self.db_path = ":memory:"
        else:
            self.db_path = Path(db_path).resolve()
            if self.db_path.parent != Path("."):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn: sqlite3.Connection | None = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is not None:
            return self._conn

        try:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
                isolation_level=None,  # autocommit mode, transactions handled explicitly
            )
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")

            if str(self.db_path) != ":memory:":
                conn.execute("PRAGMA journal_mode = WAL;")
                conn.execute("PRAGMA synchronous = NORMAL;")

            if str(self.db_path) == ":memory:":
                self._conn = conn
            return conn
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to connect to execution ledger at {self.db_path}: {exc}") from exc

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            # Check existing version
            cursor = conn.execute("PRAGMA user_version;")
            row = cursor.fetchone()
            curr_version = row[0] if row else 0

            if curr_version > SCHEMA_VERSION:
                raise LedgerCorruptionError(
                    f"Unsupported future database schema version {curr_version} (supported: {SCHEMA_VERSION})"
                )

            with conn:
                conn.execute("""
                CREATE TABLE IF NOT EXISTS missions (
                    mission_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    is_production INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
                    sprint_id TEXT NOT NULL,
                    plan_id TEXT NOT NULL,
                    project_manager_id TEXT NOT NULL,
                    task_ids_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS sprints (
                    sprint_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL UNIQUE,
                    objective TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    department_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'CREATED',
                    assigned_employee_ids_json TEXT NOT NULL DEFAULT '[]',
                    task_ids_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    plan_id TEXT PRIMARY KEY,
                    mission_id TEXT NOT NULL UNIQUE,
                    work_queue_json TEXT NOT NULL DEFAULT '[]',
                    dependency_graph_json TEXT NOT NULL DEFAULT '{}',
                    running_json TEXT NOT NULL DEFAULT '[]',
                    waiting_json TEXT NOT NULL DEFAULT '[]',
                    blocked_json TEXT NOT NULL DEFAULT '[]',
                    completed_json TEXT NOT NULL DEFAULT '[]',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS work_items (
                    work_item_id TEXT PRIMARY KEY,
                    mission_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    assigned_position_id TEXT NOT NULL,
                    assigned_employee_id TEXT,
                    status TEXT NOT NULL DEFAULT 'CREATED',
                    is_production INTEGER NOT NULL DEFAULT 0,
                    manufacturing_order_id TEXT,
                    artifact_id TEXT,
                    dependencies_json TEXT NOT NULL DEFAULT '[]',
                    recovery_status TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (mission_id) REFERENCES missions (mission_id) ON DELETE SET NULL
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS executions (
                    execution_id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL,
                    employee_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    execution_mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT,
                    provider_metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (work_item_id) REFERENCES work_items (work_item_id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL,
                    execution_id TEXT,
                    employee_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    artifact_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    parent_artifact_ids_json TEXT NOT NULL DEFAULT '[]',
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (work_item_id) REFERENCES work_items (work_item_id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS test_results (
                    test_result_id TEXT PRIMARY KEY,
                    artifact_id TEXT NOT NULL,
                    work_item_id TEXT NOT NULL,
                    command_id TEXT NOT NULL,
                    target TEXT NOT NULL,
                    exit_code INTEGER NOT NULL,
                    passed INTEGER NOT NULL,
                    duration REAL NOT NULL,
                    stdout_summary TEXT NOT NULL DEFAULT '',
                    stderr_summary TEXT NOT NULL DEFAULT '',
                    timed_out INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (artifact_id) REFERENCES artifacts (artifact_id) ON DELETE CASCADE,
                    FOREIGN KEY (work_item_id) REFERENCES work_items (work_item_id) ON DELETE CASCADE
                );
                """)

                conn.execute("""
                CREATE TABLE IF NOT EXISTS chief_approvals (
                    approval_id TEXT PRIMARY KEY,
                    work_item_id TEXT NOT NULL UNIQUE,
                    approver_id TEXT NOT NULL,
                    approver_role TEXT NOT NULL,
                    is_human INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'PRODUCTION_DEPLOYMENT',
                    approved_at TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (work_item_id) REFERENCES work_items (work_item_id) ON DELETE CASCADE
                );
                """)

                conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION};")
        except LedgerError:
            raise
        except Exception as exc:
            raise LedgerPersistenceError(f"Database initialization failed: {exc}") from exc

    def close(self) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ------------------------------------------------------------------
    # Guard / Bound Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_bounds(
        summary: str | None = None,
        git_diff: str | None = None,
        error: str | None = None,
        payload_bytes_len: int | None = None,
    ) -> None:
        if summary is not None:
            size = len(summary.encode("utf-8"))
            if size > MAX_SUMMARY_BYTES:
                raise LedgerBoundExceededError(
                    f"Summary size {size} bytes exceeds maximum limit of {MAX_SUMMARY_BYTES} bytes"
                )
        if git_diff is not None:
            size = len(git_diff.encode("utf-8"))
            if size > MAX_DIFF_BYTES:
                raise LedgerBoundExceededError(
                    f"Git diff size {size} bytes exceeds maximum limit of {MAX_DIFF_BYTES} bytes"
                )
        if error is not None:
            size = len(error.encode("utf-8"))
            if size > MAX_ERROR_BYTES:
                raise LedgerBoundExceededError(
                    f"Error message size {size} bytes exceeds maximum limit of {MAX_ERROR_BYTES} bytes"
                )
        if payload_bytes_len is not None and payload_bytes_len > MAX_PAYLOAD_BYTES:
            raise LedgerBoundExceededError(
                f"Payload size {payload_bytes_len} bytes exceeds maximum limit of {MAX_PAYLOAD_BYTES} bytes"
            )

    # ------------------------------------------------------------------
    # Write Operations (Atomic Write-Through)
    # ------------------------------------------------------------------

    def record_mission_bundle(
        self,
        mission_dict: dict[str, Any],
        sprint_dict: dict[str, Any],
        plan_dict: dict[str, Any],
        work_items: list[dict[str, Any]],
    ) -> None:
        """Atomically record a new mission, its sprint, plan, and initial work items."""
        conn = self._get_connection()
        try:
            with conn:
                # 1. Mission
                conn.execute(
                    """
                    INSERT INTO missions (
                        mission_id, title, description, is_production, status,
                        sprint_id, plan_id, project_manager_id, task_ids_json,
                        created_at, updated_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(mission_id) DO UPDATE SET
                        status=excluded.status,
                        updated_at=excluded.updated_at,
                        task_ids_json=excluded.task_ids_json,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        mission_dict["mission_id"],
                        mission_dict["title"],
                        mission_dict.get("description", ""),
                        1 if mission_dict.get("is_production") else 0,
                        mission_dict.get("status", "IN_PROGRESS"),
                        mission_dict["sprint_id"],
                        mission_dict["plan_id"],
                        mission_dict["project_manager_id"],
                        json.dumps(mission_dict.get("task_ids", [])),
                        mission_dict.get("created_at", _now()),
                        mission_dict.get("updated_at", _now()),
                        json.dumps(mission_dict.get("metadata", {})),
                    ),
                )

                # 2. Sprint
                conn.execute(
                    """
                    INSERT INTO sprints (
                        sprint_id, mission_id, objective, organization_id, department_id,
                        status, assigned_employee_ids_json, task_ids_json, metadata_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(sprint_id) DO UPDATE SET
                        status=excluded.status,
                        assigned_employee_ids_json=excluded.assigned_employee_ids_json,
                        task_ids_json=excluded.task_ids_json,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        sprint_dict["sprint_id"],
                        sprint_dict["mission_id"],
                        sprint_dict["objective"],
                        sprint_dict["organization_id"],
                        sprint_dict["department_id"],
                        sprint_dict.get("status", "CREATED"),
                        json.dumps(sprint_dict.get("assigned_employee_ids", [])),
                        json.dumps(sprint_dict.get("task_ids", [])),
                        json.dumps(sprint_dict.get("metadata", {})),
                        sprint_dict.get("created_at", _now()),
                    ),
                )

                # 3. Plan
                conn.execute(
                    """
                    INSERT INTO plans (
                        plan_id, mission_id, work_queue_json, dependency_graph_json,
                        running_json, waiting_json, blocked_json, completed_json,
                        metadata_json, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(plan_id) DO UPDATE SET
                        work_queue_json=excluded.work_queue_json,
                        dependency_graph_json=excluded.dependency_graph_json,
                        running_json=excluded.running_json,
                        waiting_json=excluded.waiting_json,
                        blocked_json=excluded.blocked_json,
                        completed_json=excluded.completed_json,
                        updated_at=excluded.updated_at,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        plan_dict["plan_id"],
                        plan_dict["mission_id"],
                        json.dumps(plan_dict.get("work_queue", [])),
                        json.dumps(plan_dict.get("dependency_graph", {})),
                        json.dumps(plan_dict.get("running", [])),
                        json.dumps(plan_dict.get("waiting", [])),
                        json.dumps(plan_dict.get("blocked", [])),
                        json.dumps(plan_dict.get("completed", [])),
                        json.dumps(plan_dict.get("metadata", {})),
                        plan_dict.get("created_at", _now()),
                        plan_dict.get("updated_at", _now()),
                    ),
                )

                # 4. Work Items
                for item in work_items:
                    conn.execute(
                        """
                        INSERT INTO work_items (
                            work_item_id, mission_id, title, description,
                            assigned_position_id, assigned_employee_id, status,
                            is_production, manufacturing_order_id, artifact_id,
                            dependencies_json, recovery_status, created_at, updated_at,
                            metadata_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(work_item_id) DO UPDATE SET
                            assigned_employee_id=excluded.assigned_employee_id,
                            status=excluded.status,
                            artifact_id=excluded.artifact_id,
                            recovery_status=excluded.recovery_status,
                            updated_at=excluded.updated_at,
                            metadata_json=excluded.metadata_json
                        """,
                        (
                            item["work_item_id"],
                            item.get("mission_id"),
                            item["title"],
                            item.get("description", ""),
                            item["assigned_position_id"],
                            item.get("assigned_employee_id"),
                            item.get("status", "CREATED"),
                            1 if item.get("is_production") else 0,
                            item.get("manufacturing_order_id"),
                            item.get("artifact_id"),
                            json.dumps(item.get("dependencies", [])),
                            item.get("recovery_status"),
                            item.get("created_at", _now()),
                            item.get("updated_at", _now()),
                            json.dumps(item.get("metadata", {})),
                        ),
                    )
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to record mission bundle: {exc}") from exc

    def record_work_item(self, item_dict: dict[str, Any]) -> None:
        """Write-through for individual work item insertion or update."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO work_items (
                        work_item_id, mission_id, title, description,
                        assigned_position_id, assigned_employee_id, status,
                        is_production, manufacturing_order_id, artifact_id,
                        dependencies_json, recovery_status, created_at, updated_at,
                        metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(work_item_id) DO UPDATE SET
                        assigned_employee_id=excluded.assigned_employee_id,
                        status=excluded.status,
                        artifact_id=excluded.artifact_id,
                        recovery_status=excluded.recovery_status,
                        updated_at=excluded.updated_at,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        item_dict["work_item_id"],
                        item_dict.get("mission_id"),
                        item_dict["title"],
                        item_dict.get("description", ""),
                        item_dict["assigned_position_id"],
                        item_dict.get("assigned_employee_id"),
                        item_dict.get("status", "CREATED"),
                        1 if item_dict.get("is_production") else 0,
                        item_dict.get("manufacturing_order_id"),
                        item_dict.get("artifact_id"),
                        json.dumps(item_dict.get("dependencies", [])),
                        item_dict.get("recovery_status"),
                        item_dict.get("created_at", _now()),
                        item_dict.get("updated_at", _now()),
                        json.dumps(item_dict.get("metadata", {})),
                    ),
                )
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to record work item '{item_dict.get('work_item_id')}': {exc}") from exc

    def update_work_item_status(
        self,
        work_item_id: str,
        status: str,
        assigned_employee_id: str | None = None,
        artifact_id: str | None = None,
        recovery_status: str | None = None,
        metadata_update: dict[str, Any] | None = None,
    ) -> None:
        """Update status and assignment of a work item."""
        conn = self._get_connection()
        try:
            with conn:
                # Fetch existing metadata to merge if requested
                if metadata_update is not None:
                    row = conn.execute("SELECT metadata_json FROM work_items WHERE work_item_id = ?", (work_item_id,)).fetchone()
                    existing_meta = json.loads(row["metadata_json"]) if row else {}
                    existing_meta.update(metadata_update)
                    meta_json = json.dumps(existing_meta)
                else:
                    meta_json = None

                query = "UPDATE work_items SET status = ?, updated_at = ?"
                params: list[Any] = [status, _now()]

                if assigned_employee_id is not None:
                    query += ", assigned_employee_id = ?"
                    params.append(assigned_employee_id)
                if artifact_id is not None:
                    query += ", artifact_id = ?"
                    params.append(artifact_id)
                if recovery_status is not None:
                    query += ", recovery_status = ?"
                    params.append(recovery_status)
                if meta_json is not None:
                    query += ", metadata_json = ?"
                    params.append(meta_json)

                query += " WHERE work_item_id = ?"
                params.append(work_item_id)
                conn.execute(query, tuple(params))
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to update work item status for '{work_item_id}': {exc}") from exc

    def update_plan_state(self, plan_dict: dict[str, Any]) -> None:
        """Update plan execution lists."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE plans SET
                        running_json = ?,
                        waiting_json = ?,
                        blocked_json = ?,
                        completed_json = ?,
                        updated_at = ?
                    WHERE plan_id = ?
                    """,
                    (
                        json.dumps(plan_dict.get("running", [])),
                        json.dumps(plan_dict.get("waiting", [])),
                        json.dumps(plan_dict.get("blocked", [])),
                        json.dumps(plan_dict.get("completed", [])),
                        _now(),
                        plan_dict["plan_id"],
                    ),
                )
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to update plan '{plan_dict.get('plan_id')}': {exc}") from exc

    def record_execution_started(
        self,
        execution_id: str,
        work_item_id: str,
        employee_id: str,
        role: str,
        execution_mode: str,
        started_at: str | None = None,
        provider_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record the start of an execution. Status is 'STARTED'."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO executions (
                        execution_id, work_item_id, employee_id, role,
                        execution_mode, status, started_at, provider_metadata_json
                    ) VALUES (?, ?, ?, ?, ?, 'STARTED', ?, ?)
                    """,
                    (
                        execution_id,
                        work_item_id,
                        employee_id,
                        role,
                        execution_mode,
                        started_at or _now(),
                        json.dumps(provider_metadata or {}),
                    ),
                )
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to record execution start: {exc}") from exc

    def record_execution_completed(
        self,
        execution_id: str,
        status: str,
        completed_at: str | None = None,
        error: str | None = None,
    ) -> None:
        """Update execution to 'SUCCESS' or 'FAILED'."""
        if error:
            self._validate_bounds(error=error)

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    UPDATE executions SET
                        status = ?,
                        completed_at = ?,
                        error = ?
                    WHERE execution_id = ?
                    """,
                    (
                        status,
                        completed_at or _now(),
                        error,
                        execution_id,
                    ),
                )
        except LedgerError:
            raise
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to record execution completion: {exc}") from exc

    def record_artifact(
        self,
        artifact_id: str,
        work_item_id: str,
        employee_id: str,
        role: str,
        artifact_type: str,
        status: str,
        summary: str,
        payload: dict[str, Any],
        parent_artifact_ids: list[str] | None = None,
        execution_id: str | None = None,
        created_at: str | None = None,
        test_results: list[dict[str, Any]] | None = None,
    ) -> None:
        """Record an artifact (ExecutionArtifact, PatchArtifact, ReviewArtifact) and any TestResults."""
        # Enforce safety bounds
        payload_str = json.dumps(payload)
        self._validate_bounds(
            summary=summary,
            git_diff=payload.get("git_diff"),
            payload_bytes_len=len(payload_str.encode("utf-8")),
        )

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO artifacts (
                        artifact_id, work_item_id, execution_id, employee_id, role,
                        artifact_type, status, summary, parent_artifact_ids_json,
                        payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(artifact_id) DO UPDATE SET
                        status=excluded.status,
                        summary=excluded.summary,
                        payload_json=excluded.payload_json
                    """,
                    (
                        artifact_id,
                        work_item_id,
                        execution_id,
                        employee_id,
                        role,
                        artifact_type,
                        status,
                        summary,
                        json.dumps(parent_artifact_ids or []),
                        payload_str,
                        created_at or _now(),
                    ),
                )

                if test_results:
                    for tr in test_results:
                        conn.execute(
                            """
                            INSERT INTO test_results (
                                test_result_id, artifact_id, work_item_id, command_id,
                                target, exit_code, passed, duration, stdout_summary,
                                stderr_summary, timed_out, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(test_result_id) DO NOTHING
                            """,
                            (
                                tr["test_result_id"],
                                artifact_id,
                                work_item_id,
                                tr["command_id"],
                                tr["target"],
                                tr["exit_code"],
                                1 if tr["passed"] else 0,
                                float(tr["duration"]),
                                tr.get("stdout_summary", "")[:MAX_SUMMARY_BYTES],
                                tr.get("stderr_summary", "")[:MAX_SUMMARY_BYTES],
                                1 if tr.get("timed_out") else 0,
                                tr.get("created_at", _now()),
                            ),
                        )
        except LedgerError:
            raise
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to record artifact '{artifact_id}': {exc}") from exc

    def record_chief_approval(
        self,
        approval_id: str,
        work_item_id: str,
        approver_id: str,
        approver_role: str,
        is_human: bool,
        status: str,
        scope: str = "PRODUCTION_DEPLOYMENT",
        approved_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record a Chief approval decision. Atomic and fail-closed."""
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO chief_approvals (
                        approval_id, work_item_id, approver_id, approver_role,
                        is_human, status, scope, approved_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(work_item_id) DO UPDATE SET
                        approval_id=excluded.approval_id,
                        approver_id=excluded.approver_id,
                        approver_role=excluded.approver_role,
                        is_human=excluded.is_human,
                        status=excluded.status,
                        scope=excluded.scope,
                        approved_at=excluded.approved_at,
                        metadata_json=excluded.metadata_json
                    """,
                    (
                        approval_id,
                        work_item_id,
                        approver_id,
                        approver_role,
                        1 if is_human else 0,
                        status,
                        scope,
                        approved_at or _now(),
                        json.dumps(metadata or {}),
                    ),
                )
        except Exception as exc:
            raise LedgerPersistenceError(f"Failed to record Chief approval for '{work_item_id}': {exc}") from exc

    # ------------------------------------------------------------------
    # Query / Rehydration Operations
    # ------------------------------------------------------------------

    def load_missions(self) -> list[dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM missions ORDER BY created_at ASC").fetchall()
        result = []
        for r in rows:
            result.append({
                "mission_id": r["mission_id"],
                "title": r["title"],
                "description": r["description"],
                "is_production": bool(r["is_production"]),
                "status": r["status"],
                "sprint_id": r["sprint_id"],
                "plan_id": r["plan_id"],
                "project_manager_id": r["project_manager_id"],
                "task_ids": json.loads(r["task_ids_json"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "metadata": json.loads(r["metadata_json"]),
            })
        return result

    def load_sprints(self) -> list[dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM sprints").fetchall()
        result = []
        for r in rows:
            result.append({
                "sprint_id": r["sprint_id"],
                "mission_id": r["mission_id"],
                "objective": r["objective"],
                "organization_id": r["organization_id"],
                "department_id": r["department_id"],
                "status": r["status"],
                "assigned_employee_ids": json.loads(r["assigned_employee_ids_json"]),
                "task_ids": json.loads(r["task_ids_json"]),
                "metadata": json.loads(r["metadata_json"]),
                "created_at": r["created_at"],
            })
        return result

    def load_plans(self) -> list[dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM plans").fetchall()
        result = []
        for r in rows:
            result.append({
                "plan_id": r["plan_id"],
                "mission_id": r["mission_id"],
                "work_queue": json.loads(r["work_queue_json"]),
                "dependency_graph": json.loads(r["dependency_graph_json"]),
                "running": json.loads(r["running_json"]),
                "waiting": json.loads(r["waiting_json"]),
                "blocked": json.loads(r["blocked_json"]),
                "completed": json.loads(r["completed_json"]),
                "metadata": json.loads(r["metadata_json"]),
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
            })
        return result

    def load_work_items(self) -> list[dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM work_items ORDER BY created_at ASC").fetchall()
        result = []
        for r in rows:
            result.append({
                "work_item_id": r["work_item_id"],
                "mission_id": r["mission_id"],
                "title": r["title"],
                "description": r["description"],
                "assigned_position_id": r["assigned_position_id"],
                "assigned_employee_id": r["assigned_employee_id"],
                "status": r["status"],
                "is_production": bool(r["is_production"]),
                "manufacturing_order_id": r["manufacturing_order_id"],
                "artifact_id": r["artifact_id"],
                "dependencies": json.loads(r["dependencies_json"]),
                "recovery_status": r["recovery_status"],
                "created_at": r["created_at"],
                "updated_at": r["updated_at"],
                "metadata": json.loads(r["metadata_json"]),
            })
        return result

    def load_executions(self, work_item_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._get_connection()
        if work_item_id:
            rows = conn.execute(
                "SELECT * FROM executions WHERE work_item_id = ? ORDER BY started_at ASC",
                (work_item_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM executions ORDER BY started_at ASC").fetchall()

        result = []
        for r in rows:
            result.append({
                "execution_id": r["execution_id"],
                "work_item_id": r["work_item_id"],
                "employee_id": r["employee_id"],
                "role": r["role"],
                "execution_mode": r["execution_mode"],
                "status": r["status"],
                "started_at": r["started_at"],
                "completed_at": r["completed_at"],
                "error": r["error"],
                "provider_metadata": json.loads(r["provider_metadata_json"]),
            })
        return result

    def get_in_flight_executions(self) -> list[dict[str, Any]]:
        """Find executions that started but never recorded completion or failure."""
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM executions WHERE status = 'STARTED' ORDER BY started_at ASC"
        ).fetchall()
        result = []
        for r in rows:
            result.append({
                "execution_id": r["execution_id"],
                "work_item_id": r["work_item_id"],
                "employee_id": r["employee_id"],
                "role": r["role"],
                "execution_mode": r["execution_mode"],
                "status": r["status"],
                "started_at": r["started_at"],
                "provider_metadata": json.loads(r["provider_metadata_json"]),
            })
        return result

    def load_artifacts(self, work_item_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._get_connection()
        if work_item_id:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE work_item_id = ? ORDER BY created_at ASC",
                (work_item_id,),
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM artifacts ORDER BY created_at ASC").fetchall()

        result = []
        for r in rows:
            art_id = r["artifact_id"]
            test_rows = conn.execute(
                "SELECT * FROM test_results WHERE artifact_id = ? ORDER BY created_at ASC",
                (art_id,),
            ).fetchall()
            test_results = []
            for tr in test_rows:
                test_results.append({
                    "test_result_id": tr["test_result_id"],
                    "command_id": tr["command_id"],
                    "target": tr["target"],
                    "exit_code": tr["exit_code"],
                    "passed": bool(tr["passed"]),
                    "duration": tr["duration"],
                    "stdout_summary": tr["stdout_summary"],
                    "stderr_summary": tr["stderr_summary"],
                    "timed_out": bool(tr["timed_out"]),
                })

            result.append({
                "artifact_id": art_id,
                "work_item_id": r["work_item_id"],
                "execution_id": r["execution_id"],
                "employee_id": r["employee_id"],
                "role": r["role"],
                "artifact_type": r["artifact_type"],
                "status": r["status"],
                "summary": r["summary"],
                "parent_artifact_ids": json.loads(r["parent_artifact_ids_json"]),
                "payload": json.loads(r["payload_json"]),
                "created_at": r["created_at"],
                "test_results": test_results,
            })
        return result

    def load_chief_approvals(self) -> list[dict[str, Any]]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM chief_approvals ORDER BY approved_at ASC").fetchall()
        result = []
        for r in rows:
            result.append({
                "approval_id": r["approval_id"],
                "work_item_id": r["work_item_id"],
                "approver_id": r["approver_id"],
                "approver_role": r["approver_role"],
                "is_human": bool(r["is_human"]),
                "status": r["status"],
                "scope": r["scope"],
                "approved_at": r["approved_at"],
                "metadata": json.loads(r["metadata_json"]),
            })
        return result

    def get_audit_trail(self, work_item_id: str) -> dict[str, Any]:
        """Reconstruct full provenance trail for a work item."""
        conn = self._get_connection()
        item_row = conn.execute("SELECT * FROM work_items WHERE work_item_id = ?", (work_item_id,)).fetchone()
        if not item_row:
            return {}

        executions = self.load_executions(work_item_id)
        artifacts = self.load_artifacts(work_item_id)
        approval_row = conn.execute("SELECT * FROM chief_approvals WHERE work_item_id = ?", (work_item_id,)).fetchone()

        return {
            "work_item_id": work_item_id,
            "title": item_row["title"],
            "status": item_row["status"],
            "assigned_position_id": item_row["assigned_position_id"],
            "assigned_employee_id": item_row["assigned_employee_id"],
            "is_production": bool(item_row["is_production"]),
            "recovery_status": item_row["recovery_status"],
            "executions": executions,
            "artifacts": artifacts,
            "chief_approval": dict(approval_row) if approval_row else None,
        }
