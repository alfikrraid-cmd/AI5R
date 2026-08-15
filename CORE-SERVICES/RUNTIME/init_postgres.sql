CREATE TABLE IF NOT EXISTS osa_runtime_state (
  id text PRIMARY KEY,
  state jsonb,
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS osa_runtime_health (
  id text PRIMARY KEY,
  health jsonb,
  updated_at timestamptz DEFAULT now()
);

CREATE TABLE IF NOT EXISTS osa_runtime_events (
  event_id text PRIMARY KEY,
  event jsonb,
  created_at timestamptz DEFAULT now()
);

-- MWO-LTSA-DATA-IMPORT-UI-001C-DURABLE -- durable backing store for
-- ImportSessionRepository (CORE-SERVICES/API/import_session_repository.py).
-- Same generic id/jsonb/timestamptz shape as osa_runtime_state above, not
-- a new pattern -- a dedicated table (not osa_runtime_state itself) so
-- Import session identity never collides with OSA's own use of that
-- table's id keyspace.
--
-- package/snapshot are the exact, frozen reviewed inputs a dry-run
-- produced (ImportPackage-shaped: pumps/seals/installations/documents,
-- each a list of raw dicts) -- immutable once written. Reconstruction
-- re-runs the SAME pure functions (validate_import_package/
-- build_conflict_report/build_canonical_packages/build_import_session,
-- all reused unmodified) against these frozen inputs, so a session
-- rebuilt after a restart is byte-for-byte identical to the one the
-- original dry-run built -- never a re-parsed XLSX, never a re-read live
-- snapshot. status is denormalized for the atomic claim (see
-- ImportSessionRepository.claim_for_execution's own docstring).
CREATE TABLE IF NOT EXISTS import_sessions (
  session_id text PRIMARY KEY,
  status text NOT NULL,
  source text,
  created_at text,
  package jsonb NOT NULL,
  snapshot jsonb NOT NULL,
  execution_result jsonb,
  updated_at timestamptz DEFAULT now()
);