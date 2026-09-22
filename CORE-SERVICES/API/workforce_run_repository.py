"""Isolated local pilot journal, not the production DB or a schema migration.

SQLite transactions serialize claims and state changes across threads/processes.
A process interrupted after claiming remains RUNNING; R1 never retries AI.
"""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def utc_now():
    return datetime.now(timezone.utc).isoformat()


class RunConflict(ValueError):
    pass


class WorkforceRunRepository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        if self.path == ":memory:":
            raise ValueError("Pilot requires durable local persistence")
        with self._transaction() as connection:
            connection.execute("""CREATE TABLE IF NOT EXISTS workforce_pilot_runs (
                run_id TEXT PRIMARY KEY, organization_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL, document TEXT NOT NULL,
                UNIQUE(organization_id, idempotency_key))""")

    @contextmanager
    def _transaction(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _load(connection, run_id):
        row = connection.execute(
            "SELECT document FROM workforce_pilot_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if row is None:
            raise KeyError("Pilot run not found")
        return json.loads(row[0])

    @staticmethod
    def _save(connection, run):
        connection.execute("UPDATE workforce_pilot_runs SET document=? WHERE run_id=?",
                           (json.dumps(run), run["run_id"]))

    def get(self, run_id):
        with self._transaction() as connection:
            return self._load(connection, run_id)

    def claim(self, *, organization_id, requester_id, idempotency_key,
              mission_type, employee, requested_policy):
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT document FROM workforce_pilot_runs WHERE organization_id=? AND idempotency_key=?",
                (organization_id, idempotency_key),
            ).fetchone()
            if row:
                run = json.loads(row[0])
                if run["requester_id"] != requester_id or run["mission_type"] != mission_type:
                    raise RunConflict("Idempotency key is already bound to another request")
                return run, False
            run = dict(
                run_id=str(uuid4()), organization_id=organization_id,
                requester_id=requester_id, idempotency_key=idempotency_key,
                mission_type=mission_type, employee=employee, status="RUNNING",
                requested_policy=requested_policy, actual_provider=None, actual_model=None,
                finish_reason=None, fallback_used=False, outcome=None,
                started_at=utc_now(), completed_at=None, elapsed_ms=None,
                safe_error=None, draft=None, draft_version=None,
                review=None, review_status="NOT_READY",
            )
            connection.execute("INSERT INTO workforce_pilot_runs VALUES (?,?,?,?)", (
                run["run_id"], organization_id, idempotency_key, json.dumps(run),
            ))
            return run, True

    def finish_execution(self, run_id, *, result, elapsed_ms, evidence=None):
        import hashlib
        with self._transaction() as connection:
            run = self._load(connection, run_id)
            if run["status"] != "RUNNING":
                raise RunConflict("Execution is no longer RUNNING")
            run["elapsed_ms"] = elapsed_ms
            run["completed_at"] = utc_now()  # AI execution completion, not review time
            if result is None:
                run.update(status="FAILED", outcome="FAILED", safe_error="Pilot AI execution failed")
            else:
                draft_sha256 = getattr(result, "draft_sha256", None) or hashlib.sha256(result.content.encode("utf-8")).hexdigest()
                run.update(status="AWAITING_REVIEW", actual_provider=result.actual_provider,
                           actual_model=result.actual_model, finish_reason=result.finish_reason,
                           fallback_used=result.fallback_used, outcome=result.outcome,
                           draft_version=1, draft_sha256=draft_sha256, review_status="PENDING")
                run["draft"] = dict(draft_id=str(uuid4()), run_id=run_id, version=1,
                                    content=result.content, sha256=draft_sha256, created_at=utc_now())
                ev = evidence or getattr(result, "evidence", None)
                if ev:
                    run["evidence_sha256"] = ev.get("evidence_sha256")
                    run["evidence_source_domains"] = ev.get("source_domains")
                    run["evidence_row_counts"] = ev.get("source_row_counts")
                    run["evidence_truncated"] = ev.get("evidence_truncated", False)
                    run["period_start"] = ev.get("period_start")
                    run["period_end"] = ev.get("period_end")
                    run["evidence"] = ev
            self._save(connection, run)
            return run

    def review(self, run_id, *, reviewer_id, decision, draft_version, note):
        if decision not in {"APPROVE", "REJECT"}:
            raise ValueError("Invalid review decision")
        with self._transaction() as connection:
            run = self._load(connection, run_id)
            if run["draft"] is None or run["draft_version"] != draft_version:
                raise RunConflict("Exact current draft version is required")
            review = dict(reviewer_id=reviewer_id, decision=decision,
                          draft_version=draft_version, note=note)
            if run["review"] is not None:
                prior = {k: run["review"][k] for k in review}
                if prior == review:
                    return run
                raise RunConflict("Terminal review is immutable")
            if run["status"] != "AWAITING_REVIEW":
                raise RunConflict("Run is not awaiting review")
            review["reviewed_at"] = utc_now()
            run.update(review=review, review_status=decision,
                       status="COMPLETED" if decision == "APPROVE" else "REJECTED")
            self._save(connection, run)
            return run
