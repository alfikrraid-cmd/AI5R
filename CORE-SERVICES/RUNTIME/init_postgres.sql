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