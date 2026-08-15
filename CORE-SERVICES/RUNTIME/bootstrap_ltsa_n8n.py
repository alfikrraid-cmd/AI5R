from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

# n8n's internal REST API (/rest/...) wraps every successful single-object
# AND list payload in {"data": ...} -- confirmed against a real, disposable
# n8n 1.115.3 instance for every endpoint this script calls: GET
# /rest/settings, POST /rest/owner/setup, POST /rest/login, GET/POST
# /rest/credentials, GET/POST/PATCH /rest/workflows. Error bodies
# (4xx/5xx) are NOT wrapped -- they are shaped {"code": int, "message":
# str} instead, so unwrapping is conditional on the "data" key actually
# being present, never assumed. This was previously unhandled for every
# single-object response except GET /rest/credentials and GET
# /rest/workflows (which happened to already do `.get("data", ...)`)
# -- POST /rest/credentials returning body["data"]["id"] rather than
# body["id"] is the exact, reproduced cause of the production
# `KeyError: 'id'` crash.
REQUIRED_OWNER_ENV_KEYS = ("AI5R_N8N_OWNER_EMAIL", "AI5R_N8N_OWNER_PASSWORD")

# This file lives at <repo_root>/CORE-SERVICES/RUNTIME/bootstrap_ltsa_n8n.py
# -- two parents up from its own resolved location is the repository root
# that WORKFLOW_SPECS' own paths (e.g. "PRODUCTS/LTSA-BRAIN/BUILD-PACKS/...")
# are relative to. Previously this script used Path.cwd() instead, which
# only worked when invoked from the repository root -- running it from
# CORE-SERVICES/RUNTIME (or any other directory) produced a real,
# reproduced FileNotFoundError trying to read a workflow source file
# under a doubled-up, nonexistent path. Deterministic from the script's
# own location, never from whatever directory happened to invoke it.
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]


WORKFLOW_SPECS = [
    {
        # MWO-LTSA-PUMP-CANONICAL-MIGRATION-001: replaces the deprecated
        # BUILD-PACKS/BP-PUMP static-response stub (pump_registry/pump_code,
        # never queried by any workflow -- see CANONICAL_SCHEMA.sql's own
        # PUMP header) with the real, ltsa_pumps-backed canonical source
        # already selected by MWO-P-004's own inventory (source path
        # confirmed there and in the deprecated stub's own
        # _canonicalReplacement metadata). "deprecated_aliases" lets
        # bootstrap_workflows find and update-in-place a workflow that a
        # prior bootstrap created under the old stub's n8n workflow name,
        # instead of orphaning it and creating a duplicate under the new
        # canonical name -- see bootstrap_workflows' own docstring.
        "key": "pump_list",
        "source": Path("PRODUCTS/LTSA-BRAIN/MODULES/PUMP/WORKFLOWS/WF-LTSA-PUMP-LIST-001.json"),
        "name": "WF-LTSA-PUMP-LIST-001",
        "deprecated_aliases": ["WF-LTSA-BRAIN-PUMP-LIST-001"],
        "method": "GET",
        "webhook_path": "ltsa/pump/list",
    },
    {
        # Already-complete canonical Detail per MWO-P-004's own inventory
        # ("Already complete -- not touched by this MWO, including its
        # deprecated counterpart") and CANONICAL_SCHEMA.sql's PUMP header --
        # reused unchanged except for the alwaysOutputData zero-row/
        # not-found safety fix (MWO-LTSA-PUMP-CANONICAL-MIGRATION-001).
        "key": "pump_detail",
        "source": Path(
            "PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-007-AI5R-WORKFLOW-GENERATOR/OUTPUTS/WF-LTSA-PUMP-DETAIL-001.json"
        ),
        "name": "WF-LTSA-PUMP-DETAIL-001",
        "deprecated_aliases": ["WF-LTSA-BRAIN-PUMP-DETAIL-001"],
        "method": "GET",
        "webhook_path": "ltsa/pump/detail",
    },
    {
        "key": "seal_list",
        "source": Path("PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL/WORKFLOWS/WF-LTSA-BRAIN-SEAL-LIST-001.json"),
        "name": "WF-LTSA-BRAIN-SEAL-LIST-001",
        "method": "GET",
        "webhook_path": "ltsa/seal/list",
    },
    {
        "key": "seal_stock_list",
        "source": Path("PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL-STOCK/WORKFLOWS/WF-LTSA-BRAIN-SEAL-STOCK-LIST-001.json"),
        "name": "WF-LTSA-BRAIN-SEAL-STOCK-LIST-001",
        "method": "GET",
        "webhook_path": "ltsa/seal-stock/list",
    },
    {
        "key": "seal_pump_compatibility_list",
        "source": Path(
            "PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-SEAL-PUMP-COMPATIBILITY/WORKFLOWS/"
            "WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-LIST-001.json"
        ),
        "name": "WF-LTSA-BRAIN-SEAL-PUMP-COMPATIBILITY-LIST-001",
        "method": "GET",
        "webhook_path": "ltsa/seal-pump-compatibility/list",
    },
]


def parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


class N8nClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.cookie_header: str | None = None

    def request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | list[Any] | None = None,
        authenticated: bool = True,
    ) -> tuple[int, dict[str, str], Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if authenticated and self.cookie_header:
            headers["Cookie"] = self.cookie_header

        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read().decode("utf-8")
                response_headers = {k: v for k, v in response.headers.items()}
                self._capture_cookie(response_headers)
                return response.status, response_headers, self._decode_body(body)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8")
            response_headers = {k: v for k, v in error.headers.items()}
            self._capture_cookie(response_headers)
            return error.code, response_headers, self._decode_body(body)

    def _capture_cookie(self, headers: dict[str, str]) -> None:
        raw_cookie = headers.get("Set-Cookie")
        if not raw_cookie:
            return
        parsed = SimpleCookie()
        parsed.load(raw_cookie)
        morsels = [f"{name}={morsel.value}" for name, morsel in parsed.items()]
        if morsels:
            self.cookie_header = "; ".join(morsels)

    @staticmethod
    def _decode_body(body: str) -> Any:
        if not body:
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body


def unwrap_data(body: Any) -> Any:
    """n8n's internal REST API wraps every successful payload in
    {"data": ...} (see this module's own header note, backed by direct
    inspection of a real n8n 1.115.3 instance). Unwraps it when present;
    returns `body` unchanged otherwise (an error body has no "data" key
    at all, so this is never a guess about which shape a given response
    "should" have -- it reflects whichever shape actually arrived)."""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


def ensure_owner_session(client: N8nClient, env: dict[str, str]) -> dict[str, Any]:
    """Idempotent, resumable owner phase.

    n8n has exactly one supported way to obtain an authenticated session
    without an existing one: POST /rest/owner/setup (only while
    showSetupOnFirstLoad is true, confirmed -- calling it again once
    setup is complete returns 400 "Instance owner already setup", never
    a usable session) or POST /rest/login (confirmed: 200 + Set-Cookie +
    {"data": {...owner...}} for correct credentials, 401 for incorrect
    ones). There is no third mechanism, and this function never attempts
    one -- it does not read or write n8n's Postgres tables directly.

    Resumability requires the SAME owner email/password across runs, so
    a subsequent run can log back in as the owner a prior run created.
    The previous implementation generated a random, never-persisted
    password on every run (secrets.choice(...)), which is exactly why
    the current stuck production instance cannot be resumed by this
    function -- that specific password no longer exists anywhere. Going
    forward, the owner identity is sourced from
    AI5R_N8N_OWNER_EMAIL/AI5R_N8N_OWNER_PASSWORD in the env file (the
    same "real secret lives in the gitignored env file, never generated
    ad hoc" convention this script already uses for the Postgres
    credential), so every run -- first-time setup or resume -- uses the
    same identity and can always log back in.
    """
    for key in REQUIRED_OWNER_ENV_KEYS:
        if not env.get(key):
            raise RuntimeError(f"Missing required variable for n8n owner bootstrap: {key}")
    email = env["AI5R_N8N_OWNER_EMAIL"]
    password = env["AI5R_N8N_OWNER_PASSWORD"]

    status, _, settings = client.request("/rest/settings", authenticated=False)
    if status != 200:
        raise RuntimeError(f"Unable to read n8n settings: {status}")
    settings_data = unwrap_data(settings)
    if not isinstance(settings_data, dict):
        raise RuntimeError("Unexpected n8n settings payload shape (no 'data' object)")

    setup_needed = bool(settings_data["userManagement"]["showSetupOnFirstLoad"])

    if setup_needed:
        payload = {
            "email": email,
            "firstName": env.get("AI5R_N8N_OWNER_FIRST_NAME", "AI5R"),
            "lastName": env.get("AI5R_N8N_OWNER_LAST_NAME", "Bootstrap"),
            "password": password,
        }
        status, _, body = client.request("/rest/owner/setup", method="POST", payload=payload, authenticated=False)
        if status != 200:
            raise RuntimeError(f"Owner setup failed with status {status}")
        if not client.cookie_header:
            raise RuntimeError("Owner setup succeeded but no auth cookie was issued by n8n.")
        owner_data = unwrap_data(body)
        return {
            "mode": "created",
            "showSetupOnFirstLoad_before": True,
            "owner_id": owner_data.get("id") if isinstance(owner_data, dict) else None,
            "owner_email": owner_data.get("email") if isinstance(owner_data, dict) else None,
        }

    # Resume: owner already exists. The only supported way to obtain a
    # session for an already-set-up instance is POST /rest/login -- never
    # a direct database write, never a re-run of owner/setup (which n8n
    # itself rejects once setup is complete).
    status, _, body = client.request(
        "/rest/login",
        method="POST",
        payload={"emailOrLdapLoginId": email, "password": password},
        authenticated=False,
    )
    if status != 200:
        raise RuntimeError(
            "n8n owner setup was already completed by a previous run, and this run could not "
            f"authenticate as the configured owner via POST /rest/login (status {status}). "
            "This script never bypasses n8n authentication or writes to n8n's database directly, "
            "so resuming requires AI5R_N8N_OWNER_EMAIL/AI5R_N8N_OWNER_PASSWORD to match the "
            "credentials the owner was actually created with."
        )
    if not client.cookie_header:
        raise RuntimeError("Login succeeded but no auth cookie was issued by n8n.")
    owner_data = unwrap_data(body)
    return {
        "mode": "resumed",
        "showSetupOnFirstLoad_before": False,
        "owner_id": owner_data.get("id") if isinstance(owner_data, dict) else None,
        "owner_email": owner_data.get("email") if isinstance(owner_data, dict) else None,
    }


def get_or_create_postgres_credential(client: N8nClient, env: dict[str, str]) -> dict[str, Any]:
    """Idempotent: reuses the existing "Postgres account" credential by
    name+type when present, never duplicates it. Error messages never
    include the raw response body -- a credential payload (request or
    response) can carry the connection password / n8n's own encrypted
    blob of it, so only the HTTP status is ever surfaced on failure,
    consistent with this script's "no secret in logs/report/exceptions"
    rule."""
    status, _, credentials = client.request("/rest/credentials")
    if status != 200:
        raise RuntimeError(f"Unable to list n8n credentials: {status}")
    credentials = unwrap_data(credentials)
    if not isinstance(credentials, list):
        raise RuntimeError("Unexpected n8n credentials payload shape (expected a list)")

    for credential in credentials:
        if credential.get("name") == "Postgres account" and credential.get("type") == "postgres":
            return {"id": credential["id"], "name": credential["name"], "created": False}

    required_keys = (
        "AI5R_LTSA_POSTGRES_DB",
        "AI5R_POSTGRES_USER",
        "AI5R_POSTGRES_PASSWORD",
    )
    for key in required_keys:
        if not env.get(key):
            raise RuntimeError(f"Missing required variable for LTSA n8n Postgres credential: {key}")

    payload = {
        "name": "Postgres account",
        "type": "postgres",
        "data": {
            "host": "postgres",
            "database": env["AI5R_LTSA_POSTGRES_DB"],
            "user": env["AI5R_POSTGRES_USER"],
            "password": env["AI5R_POSTGRES_PASSWORD"],
            "port": int(env.get("AI5R_POSTGRES_PORT", "5432")),
            "maxConnections": 100,
            "allowUnauthorizedCerts": False,
            "ssl": "disable",
        },
    }
    status, _, created = client.request("/rest/credentials", method="POST", payload=payload)
    if status != 200:
        raise RuntimeError(f"Unable to create Postgres credential: {status}")
    created_data = unwrap_data(created)
    if not isinstance(created_data, dict) or "id" not in created_data or "name" not in created_data:
        raise RuntimeError("Unexpected n8n credential-creation payload shape (missing 'id'/'name')")
    return {"id": created_data["id"], "name": created_data["name"], "created": True}


WEBHOOK_NODE_TYPE = "n8n-nodes-base.webhook"
POSTGRES_NODE_TYPE = "n8n-nodes-base.postgres"


def _validate_postgres_zero_row_safety(workflow: dict[str, Any], source: Path) -> None:
    """A Postgres node (operation="executeQuery") feeding a webhook's
    response chain, with no `alwaysOutputData`, silently breaks that
    chain whenever the query returns zero rows -- proven against a real,
    disposable n8n 1.115.3 instance (MWO-LTSA-PROD-ZERO-ROW-001): n8n's
    execution engine does not run a downstream node when every upstream
    connection feeding it produced zero items, so a zero-row query means
    the Code/Respond-to-Webhook nodes downstream of it never execute at
    all -- confirmed directly from a real execution's own runData, whose
    `lastNodeExecuted` was the Postgres node itself. The webhook caller
    then receives n8n's own fallback: HTTP 200 with a completely empty
    body, which is exactly what caused
    `json.decoder.JSONDecodeError: Expecting value` in every gateway
    that called json.loads() on it.

    `alwaysOutputData: true` on the Postgres node is the fix (proven:
    without it, the chain never reaches Respond to Webhook at all; with
    it, the chain runs and a deterministic {"success": true, "data": []}
    is produced) -- this validator only checks for the field's presence,
    a structural, deterministic JSON check, never a guess about a
    workflow's runtime behavior. It only applies to a workflow that
    genuinely has both a webhook trigger and a Postgres executeQuery
    node -- a workflow with neither is unaffected by this mechanism and
    is never flagged."""
    node_types = {node.get("type") for node in workflow.get("nodes", [])}
    if WEBHOOK_NODE_TYPE not in node_types or POSTGRES_NODE_TYPE not in node_types:
        return

    for node in workflow.get("nodes", []):
        if node.get("type") != POSTGRES_NODE_TYPE:
            continue
        if node.get("parameters", {}).get("operation") != "executeQuery":
            continue
        if not node.get("alwaysOutputData"):
            raise RuntimeError(
                f"Canonical workflow source {source} has a Postgres query node "
                f"({node.get('name', node.get('id', '<unnamed>'))}) feeding a webhook "
                "response chain with no alwaysOutputData. A zero-row query result would "
                "silently break the chain before Respond to Webhook ever runs, producing "
                "HTTP 200 with an empty body -- fix the canonical workflow JSON to set "
                "alwaysOutputData=true on this node (and ensure the downstream Code node "
                "filters out the resulting placeholder empty item), never patch around "
                "this in the bootstrap client or the API gateway."
            )


def _validate_webhook_nodes(workflow: dict[str, Any], source: Path) -> None:
    """A webhook trigger node with no `webhookId` of its own is a proven
    production-readiness defect, not a stylistic omission: confirmed
    against a real, disposable n8n 1.115.3 instance (positive AND
    negative controlled experiments -- see
    CORE-SERVICES/RUNTIME/TESTS/test_bootstrap_ltsa_n8n.py's own
    regression test for the reproduction). Without it, n8n registers the
    workflow's production webhook_entity row under a synthetic,
    workflow-ID-prefixed compound path instead of the clean static path
    declared in `parameters.path` -- the workflow reports active=true
    and n8n's own startup log reports it activated, but the real
    production URL clients call returns 404 "webhook is not registered"
    forever, with no error logged anywhere in the process. Failing loudly
    here, before any POST/PATCH is even sent, is strictly stronger
    verification than only catching this after activation -- it is not
    a workaround for the missing field, and it never invents one on the
    caller's behalf (see this module's own "never fabricate" discipline
    already established for credential/owner secrets)."""
    for node in workflow.get("nodes", []):
        if node.get("type") != WEBHOOK_NODE_TYPE:
            continue
        if not node.get("webhookId"):
            raise RuntimeError(
                f"Canonical workflow source {source} has a webhook node "
                f"({node.get('name', node.get('id', '<unnamed>'))}) with no webhookId. "
                "n8n 1.115.3 registers such a webhook under a synthetic, unreachable path "
                "instead of its declared production path -- fix the canonical workflow JSON "
                "to include a webhookId (e.g. a stable, unique slug like other canonical "
                "workflows already use), never patch around this in the bootstrap client."
            )


def load_workflow_source(source: Path, credential: dict[str, Any]) -> dict[str, Any]:
    workflow = json.loads(source.read_text(encoding="utf-8"))
    _validate_webhook_nodes(workflow, source)
    _validate_postgres_zero_row_safety(workflow, source)
    for node in workflow.get("nodes", []):
        credentials = node.get("credentials")
        if not isinstance(credentials, dict):
            continue
        if "postgres" in credentials:
            credentials["postgres"] = {
                "id": credential["id"],
                "name": credential["name"],
            }
    return {
        "name": workflow["name"],
        "nodes": workflow["nodes"],
        "connections": workflow["connections"],
        "settings": workflow.get("settings", {}),
        "active": False,
    }


def get_workflows_by_name(client: N8nClient) -> dict[str, dict[str, Any]]:
    status, _, payload = client.request("/rest/workflows")
    if status != 200:
        raise RuntimeError(f"Unable to list n8n workflows: {status} {payload}")
    data = unwrap_data(payload)
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected n8n workflows payload shape (expected a list): {payload}")
    return {workflow["name"]: workflow for workflow in data}


def activate_workflow(client: N8nClient, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    status, _, current = client.request(f"/rest/workflows/{workflow_id}")
    if status != 200:
        raise RuntimeError(f"Unable to load workflow {workflow_id} for activation: {status} {current}")
    current_data = unwrap_data(current)
    if not isinstance(current_data, dict):
        raise RuntimeError(f"Unexpected n8n workflow payload shape for {workflow_id}: {current}")

    activation_payload = {
        "name": current_data["name"],
        "nodes": current_data["nodes"],
        "connections": current_data["connections"],
        "settings": current_data.get("settings") or {},
        "active": True,
        "versionId": current_data.get("versionId"),
    }
    status, _, activated = client.request(
        f"/rest/workflows/{workflow_id}",
        method="PATCH",
        payload=activation_payload,
    )
    if status != 200:
        raise RuntimeError(f"Unable to activate workflow {workflow_id}: {status} {activated}")
    activated_data = unwrap_data(activated)
    if not isinstance(activated_data, dict):
        raise RuntimeError(f"Unexpected n8n workflow-activation payload shape for {workflow_id}: {activated}")
    return activated_data


def bootstrap_workflows(
    client: N8nClient,
    root: Path,
    credential: dict[str, Any],
    specs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Idempotent: creates a workflow only when no workflow of that
    canonical name exists yet (detected via GET /rest/workflows,
    matched by name); an existing one is updated in place (PATCH) and
    (re-)activated, never duplicated via a second POST. `specs` defaults
    to the real WORKFLOW_SPECS -- overridable so tests can exercise this
    function against a small, self-contained fixture set instead of all
    five real production workflow files.

    A spec may declare "deprecated_aliases": [old_n8n_workflow_name, ...]
    (MWO-LTSA-PUMP-CANONICAL-MIGRATION-001) -- checked only when no
    workflow matches the spec's own (canonical) name. This lets a
    migration that renames a deprecated stub's n8n workflow (e.g.
    "WF-LTSA-BRAIN-PUMP-LIST-001") to its canonical name (e.g.
    "WF-LTSA-PUMP-LIST-001") find and PATCH that SAME workflow ID in
    place instead of orphaning it and POSTing a duplicate under the new
    name. Once a workflow has been renamed by a prior run, the primary
    (canonical-name) lookup finds it directly on every subsequent run --
    the alias path is only ever exercised on the one migration run that
    still finds the old name, never after, so this can never itself
    produce a duplicate."""
    specs = WORKFLOW_SPECS if specs is None else specs
    existing_by_name = get_workflows_by_name(client)
    summary = {
        "created": [],
        "updated": [],
        "activated": [],
        "unchanged": [],
    }

    for spec in specs:
        source_path = root / spec["source"]
        payload = load_workflow_source(source_path, credential)
        existing = existing_by_name.get(spec["name"])
        if existing is None:
            for alias in spec.get("deprecated_aliases", []):
                existing = existing_by_name.get(alias)
                if existing is not None:
                    break

        if existing is None:
            status, _, created = client.request("/rest/workflows", method="POST", payload=payload)
            if status != 200:
                raise RuntimeError(f"Unable to create workflow {spec['name']}: {status} {created}")
            created_data = unwrap_data(created)
            if not isinstance(created_data, dict) or "id" not in created_data:
                raise RuntimeError(
                    f"Unexpected n8n workflow-creation payload shape for {spec['name']}: {created}"
                )
            workflow_id = created_data["id"]
            summary["created"].append(spec["name"])
        else:
            workflow_id = existing["id"]
            status, _, updated = client.request(f"/rest/workflows/{workflow_id}", method="PATCH", payload=payload)
            if status != 200:
                raise RuntimeError(f"Unable to update workflow {spec['name']}: {status} {updated}")
            updated_data = unwrap_data(updated)
            if not isinstance(updated_data, dict):
                raise RuntimeError(f"Unexpected n8n workflow-update payload shape for {spec['name']}: {updated}")
            summary["updated"].append(spec["name"])

        activated = activate_workflow(client, workflow_id, payload)
        if activated.get("active"):
            summary["activated"].append(spec["name"])

    after = get_workflows_by_name(client)
    summary["total_after"] = len(after)
    return summary


def call_json(url: str) -> tuple[int | None, Any]:
    """Probes one verification URL. Never raises: an HTTP error response
    (4xx/5xx) and a connection-level failure (refused/unreachable/DNS/
    timeout -- urllib.error.URLError, HTTPError's own parent class, not
    a subclass of it) are both legitimate, expected outcomes for a
    verification step whose entire purpose is to discover endpoints that
    are not (yet) reachable -- neither should abort the whole bootstrap
    report. status is None only for the connection-level case, where
    there was no HTTP response to have a status at all."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            try:
                return response.status, json.loads(body)
            except json.JSONDecodeError:
                # A 200 with an empty/non-JSON body is a real, observed
                # outcome (e.g. a workflow execution error after the
                # webhook trigger accepted the request but before the
                # Respond node ran) -- report it, never crash the whole
                # bootstrap over one verification probe.
                return response.status, body
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body)
        except json.JSONDecodeError:
            return error.code, body
    except urllib.error.URLError as error:
        return None, {"error": str(error.reason)}


def _is_valid_api_health_response(status: int | None, body: Any) -> bool:
    """The real GET /health contract (routers/health.py's HealthResponse)
    is a JSON object with a "status" key. Proven, reproduced gap: nginx's
    public routing table had no dedicated /health location, so the
    request fell through to the dashboard SPA's catch-all route and
    returned its index.html -- HTTP 200, but not the API's health at
    all. A bare `status == 200` check cannot tell these apart; this
    checks the actual decoded body shape, not just the status code."""
    return status == 200 and isinstance(body, dict) and "status" in body


def verify_runtime(env: dict[str, str]) -> dict[str, Any]:
    api_base = env["AI5R_API_PUBLIC_URL"].rstrip("/")
    n8n_base = env["AI5R_N8N_PUBLIC_URL"].rstrip("/")
    urls = {
        "api_health": f"{api_base}/health",
        "api_pumps": f"{api_base}/api/ltsa/pumps",
        "api_pump_300": f"{api_base}/api/ltsa/pumps/300-P-1A",
        "api_pump_211": f"{api_base}/api/ltsa/pumps/211-P-1A",
        "api_pump_spare_300": f"{api_base}/api/ltsa/pumps/300-P-1A/spare-parts",
        "api_pump_spare_945": f"{api_base}/api/ltsa/pumps/945-P-7A/spare-parts",
        "api_seals": f"{api_base}/api/ltsa/seals",
        "api_seal_stock": f"{api_base}/api/ltsa/seal-stock",
        "api_seal_compatibility": f"{api_base}/api/ltsa/seal-compatibility",
        "n8n_pump_list": f"{n8n_base}/webhook/ltsa/pump/list",
        "n8n_pump_detail_300": f"{n8n_base}/webhook/ltsa/pump/detail?tag_number=300-P-1A",
        "n8n_pump_detail_211": f"{n8n_base}/webhook/ltsa/pump/detail?tag_number=211-P-1A",
        "n8n_seal_list": f"{n8n_base}/webhook/ltsa/seal/list",
        "n8n_seal_stock_list": f"{n8n_base}/webhook/ltsa/seal-stock/list",
        "n8n_seal_compatibility_list": f"{n8n_base}/webhook/ltsa/seal-pump-compatibility/list",
    }
    results = {}
    for key, url in urls.items():
        status, body = call_json(url)
        result: dict[str, Any] = {"status": status, "body": body}
        if key == "api_health":
            # Never accept a 200 status alone as proof of health -- see
            # _is_valid_api_health_response's own docstring. Recorded
            # here (not raised) so the report stays the authoritative,
            # complete record of what verification actually found,
            # consistent with every other probe in this function.
            result["valid"] = _is_valid_api_health_response(status, body)
        results[key] = result
    return results


def build_inventory(root: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for spec in WORKFLOW_SPECS:
        workflow = json.loads((root / spec["source"]).read_text(encoding="utf-8"))
        credential_dependency = []
        for node in workflow.get("nodes", []):
            creds = node.get("credentials")
            if isinstance(creds, dict) and "postgres" in creds:
                credential_dependency.append(creds["postgres"])
        inventory.append(
            {
                "source_json_path": str(spec["source"]).replace("\\", "/"),
                "workflow_name": workflow["name"],
                "webhook_path": spec["webhook_path"],
                "http_method": spec["method"],
                "active_in_source": bool(workflow.get("active", False)),
                "credential_dependency": credential_dependency,
            }
        )
    return inventory


def run_bootstrap(env: dict[str, str], root: Path) -> dict[str, Any]:
    """The full, idempotent, resumable bootstrap sequence. Every phase
    (owner, credential, workflows) detects and reuses existing state
    rather than assuming a pristine instance -- safe to run against a
    fresh n8n, a partially-bootstrapped one (any subset of owner/
    credential/workflows already present), or a fully-bootstrapped one.
    Raises RuntimeError (never a bare KeyError/AttributeError from an
    unexpected response shape) on any phase failure; no report is built
    or returned in that case -- the caller only ever gets/writes a
    report after every phase has genuinely succeeded."""
    client = N8nClient(env["AI5R_N8N_PUBLIC_URL"])

    owner_context = ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)
    first = bootstrap_workflows(client, root, credential)
    verification = verify_runtime(env)
    second = bootstrap_workflows(client, root, credential)

    return {
        "owner_context": owner_context,
        "credential": {
            "name": credential["name"],
            "id": credential["id"],
            "created_on_first_bootstrap": credential["created"],
        },
        "workflow_inventory": build_inventory(root),
        "first_bootstrap": first,
        "verification": verification,
        "second_bootstrap": second,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--repo-root",
        default=None,
        help=(
            "Repository root that WORKFLOW_SPECS source paths are relative "
            "to. Defaults to this script's own location (two directories "
            "up), never the invoking shell's current working directory -- "
            "safe to run from the repository root, CORE-SERVICES/RUNTIME, "
            "or any other directory without this flag."
        ),
    )
    args = parser.parse_args()

    env = parse_env_file(Path(args.env_file))
    repo_root = Path(args.repo_root).resolve() if args.repo_root else DEFAULT_REPO_ROOT

    try:
        report = run_bootstrap(env, repo_root)
    except RuntimeError as error:
        # Every RuntimeError raised anywhere in this module is
        # constructed without embedding request/response bodies that
        # could carry a password or encrypted-credential blob (see each
        # function's own docstring) -- safe to print in full. No report
        # file is written on failure: a bootstrap report is evidence of
        # a *completed* bootstrap, never a partial one.
        print(f"Bootstrap failed: {error}", file=sys.stderr)
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
