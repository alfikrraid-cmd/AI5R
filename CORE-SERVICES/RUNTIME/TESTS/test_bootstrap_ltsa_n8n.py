import json
import sys
from pathlib import Path

import pytest

RUNTIME_DIR = Path(__file__).resolve().parents[1]
if str(RUNTIME_DIR) not in sys.path:
    sys.path.insert(0, str(RUNTIME_DIR))

import bootstrap_ltsa_n8n
from bootstrap_ltsa_n8n import (
    DEFAULT_REPO_ROOT,
    POSTGRES_NODE_TYPE,
    WEBHOOK_NODE_TYPE,
    WORKFLOW_SPECS,
    activate_workflow,
    bootstrap_workflows,
    ensure_owner_session,
    get_or_create_postgres_credential,
    get_workflows_by_name,
    load_workflow_source,
    unwrap_data,
    verify_runtime,
)

REPO_ROOT = RUNTIME_DIR.parents[1]


# --- FakeN8nClient -----------------------------------------------------
#
# Reproduces the REAL n8n 1.115.3 REST envelope shapes captured against a
# disposable instance (see bootstrap_ltsa_n8n.py's own module header):
# every successful single-object/list payload is wrapped in
# {"data": ...}; error bodies are {"code": int, "message": str}, never
# wrapped. This replaces the previous test file's fake, which returned a
# flat (unwrapped) credential-creation body -- a shape that does not
# match production and is exactly why the old test suite did not catch
# the `KeyError: 'id'` this file's tests now guard against.


class FakeN8nClient:
    def __init__(
        self,
        *,
        setup_needed: bool = True,
        owner: dict | None = None,
        owner_password: str | None = None,
        credentials: list | None = None,
        workflows: list | None = None,
    ):
        self.setup_needed = setup_needed
        self.owner = owner
        self.owner_password = owner_password
        self.credentials = credentials if credentials is not None else []
        self.workflows = workflows if workflows is not None else []
        self.cookie_header: str | None = None
        self.calls: list[tuple[str, str]] = []
        self._next_credential_id = 1
        self._next_workflow_id = 100

    def request(self, path, *, method="GET", payload=None, authenticated=True):
        self.calls.append((method, path))

        if path == "/rest/settings" and method == "GET":
            return 200, {}, {"data": {"userManagement": {"showSetupOnFirstLoad": self.setup_needed}}}

        if path == "/rest/owner/setup" and method == "POST":
            if not self.setup_needed:
                return 400, {}, {"code": 400, "message": "Instance owner already setup"}
            self.owner = {"id": "owner-1", "email": payload["email"]}
            self.owner_password = payload["password"]
            self.setup_needed = False
            self.cookie_header = "n8n-auth=fake-session-token"
            return (
                200,
                {},
                {"data": {**self.owner, "firstName": payload["firstName"], "lastName": payload["lastName"]}},
            )

        if path == "/rest/login" and method == "POST":
            if (
                self.owner is not None
                and payload.get("emailOrLdapLoginId") == self.owner["email"]
                and payload.get("password") == self.owner_password
            ):
                self.cookie_header = "n8n-auth=fake-session-token"
                return 200, {}, {"data": dict(self.owner)}
            return 401, {}, {"code": 401, "message": "Wrong username or password. Do you have caps lock on?"}

        if path == "/rest/credentials" and method == "GET":
            return 200, {}, {"data": list(self.credentials)}

        if path == "/rest/credentials" and method == "POST":
            record = {
                "id": f"cred-{self._next_credential_id}",
                "name": payload["name"],
                "type": payload["type"],
            }
            self._next_credential_id += 1
            self.credentials.append(record)
            return 200, {}, {"data": record}

        if path == "/rest/workflows" and method == "GET":
            return 200, {}, {"count": len(self.workflows), "data": list(self.workflows)}

        if path == "/rest/workflows" and method == "POST":
            workflow = {
                "id": f"wf-{self._next_workflow_id}",
                "name": payload["name"],
                "nodes": payload["nodes"],
                "connections": payload["connections"],
                "settings": payload.get("settings", {}),
                "active": payload.get("active", False),
                "versionId": "v1",
            }
            self._next_workflow_id += 1
            self.workflows.append(workflow)
            return 200, {}, {"data": dict(workflow)}

        if path.startswith("/rest/workflows/") and method == "GET":
            workflow_id = path.rsplit("/", 1)[-1]
            for workflow in self.workflows:
                if workflow["id"] == workflow_id:
                    return 200, {}, {"data": dict(workflow)}
            return 404, {}, {"code": 404, "message": "Not Found"}

        if path.startswith("/rest/workflows/") and method == "PATCH":
            workflow_id = path.rsplit("/", 1)[-1]
            for workflow in self.workflows:
                if workflow["id"] == workflow_id:
                    for key, value in payload.items():
                        if key != "versionId":
                            workflow[key] = value
                    current_version = int(workflow["versionId"][1:])
                    workflow["versionId"] = f"v{current_version + 1}"
                    return 200, {}, {"data": dict(workflow)}
            return 404, {}, {"code": 404, "message": "Not Found"}

        raise AssertionError(f"unexpected request: {method} {path}")


# --- env fixtures --------------------------------------------------------


def credential_env(**overrides):
    env = {
        "AI5R_POSTGRES_DB": "ai5r_runtime",
        "AI5R_LTSA_POSTGRES_DB": "ltsa_brain",
        "AI5R_POSTGRES_USER": "ai5r",
        "AI5R_POSTGRES_PASSWORD": "postgres-secret",
        "AI5R_POSTGRES_PORT": "15432",
    }
    env.update(overrides)
    return env


def owner_env(**overrides):
    env = {
        "AI5R_N8N_OWNER_EMAIL": "ai5r-bootstrap@example.invalid",
        "AI5R_N8N_OWNER_PASSWORD": "Test-Owner-Password-123!",
    }
    env.update(overrides)
    return env


def full_env(**overrides):
    env = {**owner_env(), **credential_env()}
    env.update(overrides)
    return env


CREDENTIAL = {"id": "cred-1", "name": "Postgres account"}


def _write_workflow_fixture(directory: Path, name: str, *, with_postgres_node: bool = True) -> None:
    nodes = [{"name": "Webhook", "type": "n8n-nodes-base.webhook", "webhookId": f"webhookid-{name.lower()}"}]
    if with_postgres_node:
        nodes.append(
            {
                "name": "Postgres",
                "type": "n8n-nodes-base.postgres",
                "credentials": {"postgres": {"id": "placeholder", "name": "placeholder"}},
            }
        )
    workflow = {"name": name, "nodes": nodes, "connections": {}, "settings": {}}
    (directory / f"{name}.json").write_text(json.dumps(workflow), encoding="utf-8")


def _specs(tmp_path: Path, names: list[str]) -> list[dict]:
    specs = []
    for name in names:
        _write_workflow_fixture(tmp_path, name)
        specs.append(
            {"source": Path(f"{name}.json"), "name": name, "method": "GET", "webhook_path": f"ltsa/{name.lower()}"}
        )
    return specs


# --- unwrap_data -----------------------------------------------------------


def test_unwrap_data_unwraps_a_single_object_envelope():
    assert unwrap_data({"data": {"id": "x"}}) == {"id": "x"}


def test_unwrap_data_unwraps_a_list_envelope():
    assert unwrap_data({"data": [1, 2, 3]}) == [1, 2, 3]


def test_unwrap_data_leaves_an_error_body_without_a_data_key_unchanged():
    # Real n8n error shape: {"code": int, "message": str}, never wrapped.
    assert unwrap_data({"code": 400, "message": "bad"}) == {"code": 400, "message": "bad"}


def test_unwrap_data_leaves_non_dict_bodies_unchanged():
    assert unwrap_data("plain text") == "plain text"
    assert unwrap_data(None) is None


# --- credential: the exact production regression --------------------------


def test_credential_creation_unwraps_the_real_n8n_data_envelope_regression():
    """Reproduces the exact shape a real n8n 1.115.3 instance returns for
    POST /rest/credentials -- {"data": {"id": ..., "name": ..., ...}} --
    captured directly against a disposable instance. The previous
    implementation did `created["id"]` against this exact shape, raising
    KeyError: 'id' in production."""
    client = FakeN8nClient()

    result = get_or_create_postgres_credential(client, credential_env())

    assert result == {"id": "cred-1", "name": "Postgres account", "created": True}


def test_existing_postgres_credential_is_reused_and_never_duplicated():
    client = FakeN8nClient(credentials=[{"id": "existing", "name": "Postgres account", "type": "postgres"}])

    result = get_or_create_postgres_credential(client, credential_env())

    assert result == {"id": "existing", "name": "Postgres account", "created": False}
    assert len(client.credentials) == 1
    assert ("POST", "/rest/credentials") not in client.calls


def test_missing_ltsa_database_configuration_fails_clearly():
    client = FakeN8nClient()
    env = credential_env(AI5R_LTSA_POSTGRES_DB="")

    with pytest.raises(RuntimeError, match="AI5R_LTSA_POSTGRES_DB"):
        get_or_create_postgres_credential(client, env)


# --- owner: creation, resume, and the production regression ---------------


def test_owner_setup_unwraps_the_real_n8n_data_envelope_regression():
    """POST /rest/owner/setup also returns {"data": {...}} against a real
    n8n 1.115.3 instance. The previous implementation's `body.get("id")`
    silently returned None against this shape (a quieter sibling of the
    credential KeyError -- no crash, but owner_id was always null)."""
    client = FakeN8nClient(setup_needed=True)

    result = ensure_owner_session(client, owner_env())

    assert result["mode"] == "created"
    assert result["owner_id"] == "owner-1"
    assert result["owner_email"] == "ai5r-bootstrap@example.invalid"
    assert client.cookie_header is not None


def test_missing_owner_email_fails_clearly():
    client = FakeN8nClient(setup_needed=True)

    with pytest.raises(RuntimeError, match="AI5R_N8N_OWNER_EMAIL"):
        ensure_owner_session(client, owner_env(AI5R_N8N_OWNER_EMAIL=""))


def test_missing_owner_password_fails_clearly():
    client = FakeN8nClient(setup_needed=True)

    with pytest.raises(RuntimeError, match="AI5R_N8N_OWNER_PASSWORD"):
        ensure_owner_session(client, owner_env(AI5R_N8N_OWNER_PASSWORD=""))


def test_owner_phase_resumes_via_login_when_the_owner_already_exists():
    # Production state: showSetupOnFirstLoad=False, owner already exists.
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="Test-Owner-Password-123!",
    )

    result = ensure_owner_session(client, owner_env())

    assert result["mode"] == "resumed"
    assert result["owner_id"] == "owner-1"
    assert client.cookie_header is not None
    assert ("POST", "/rest/owner/setup") not in client.calls
    assert ("POST", "/rest/login") in client.calls


def test_owner_phase_never_retries_setup_once_it_is_already_complete():
    # n8n itself rejects a second owner/setup call once complete (400
    # "Instance owner already setup") -- this asserts the client-side
    # branch never even attempts it, not just that it would fail cleanly.
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="Test-Owner-Password-123!",
    )

    ensure_owner_session(client, owner_env())

    assert all(call != ("POST", "/rest/owner/setup") for call in client.calls)


def test_owner_phase_fails_clearly_when_resume_login_credentials_do_not_match():
    # Models the actual stuck-production scenario: the owner exists, but
    # the password this run has (an env-configured guess) does not match
    # whatever password the owner was really created with.
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="the-real-original-password",
    )
    env = owner_env(AI5R_N8N_OWNER_PASSWORD="a-different-guessed-password")

    with pytest.raises(RuntimeError, match="POST /rest/login"):
        ensure_owner_session(client, env)


# --- secret safety -----------------------------------------------------


def test_bootstrap_report_data_never_contains_the_owner_or_postgres_password(tmp_path):
    client = FakeN8nClient()
    env = full_env()
    specs = _specs(tmp_path, ["WF-SECRET-CHECK"])

    owner_context = ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)
    workflow_summary = bootstrap_workflows(client, tmp_path, credential, specs=specs)

    serialized = json.dumps(
        {"owner_context": owner_context, "credential": credential, "workflows": workflow_summary},
        default=str,
    )
    assert env["AI5R_N8N_OWNER_PASSWORD"] not in serialized
    assert env["AI5R_POSTGRES_PASSWORD"] not in serialized


def test_owner_login_failure_message_never_contains_either_password():
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="the-real-original-password",
    )
    env = owner_env(AI5R_N8N_OWNER_PASSWORD="a-different-guessed-password")

    with pytest.raises(RuntimeError) as excinfo:
        ensure_owner_session(client, env)

    assert "the-real-original-password" not in str(excinfo.value)
    assert "a-different-guessed-password" not in str(excinfo.value)


def test_credential_creation_failure_message_never_contains_the_password():
    class FailingClient(FakeN8nClient):
        def request(self, path, *, method="GET", payload=None, authenticated=True):
            if path == "/rest/credentials" and method == "POST":
                return 500, {}, {"code": 0, "message": "internal error"}
            return super().request(path, method=method, payload=payload, authenticated=authenticated)

    client = FailingClient()
    env = credential_env()

    with pytest.raises(RuntimeError) as excinfo:
        get_or_create_postgres_credential(client, env)

    assert env["AI5R_POSTGRES_PASSWORD"] not in str(excinfo.value)


# --- workflows: idempotency, activation, envelope regression --------------


def test_workflow_creation_unwraps_the_real_n8n_data_envelope_and_activates(tmp_path):
    """POST /rest/workflows and PATCH /rest/workflows/{id} both return
    {"data": {...}} against a real n8n 1.115.3 instance -- the previous
    implementation's `created["id"]` / `current["name"]` / `activated.
    get("active")` all silently mishandled this shape (a KeyError on
    create, and a permanently-false activation status)."""
    client = FakeN8nClient()
    specs = _specs(tmp_path, ["WF-A", "WF-B"])

    summary = bootstrap_workflows(client, tmp_path, CREDENTIAL, specs=specs)

    assert summary["created"] == ["WF-A", "WF-B"]
    assert summary["updated"] == []
    assert summary["activated"] == ["WF-A", "WF-B"]
    assert summary["total_after"] == 2
    assert all(workflow["active"] for workflow in client.workflows)


def test_workflow_creation_wires_the_real_credential_id_and_name_into_postgres_nodes(tmp_path):
    client = FakeN8nClient()
    specs = _specs(tmp_path, ["WF-WITH-DB"])

    bootstrap_workflows(client, tmp_path, CREDENTIAL, specs=specs)

    postgres_node = next(n for n in client.workflows[0]["nodes"] if n["type"] == "n8n-nodes-base.postgres")
    assert postgres_node["credentials"]["postgres"] == {"id": "cred-1", "name": "Postgres account"}


def test_bootstrap_workflows_updates_and_reactivates_an_existing_workflow_never_duplicating(tmp_path):
    specs = _specs(tmp_path, ["WF-A"])
    client = FakeN8nClient(
        workflows=[
            {
                "id": "wf-existing",
                "name": "WF-A",
                "nodes": [],
                "connections": {},
                "settings": {},
                "active": True,
                "versionId": "v1",
            }
        ]
    )

    summary = bootstrap_workflows(client, tmp_path, CREDENTIAL, specs=specs)

    assert summary["created"] == []
    assert summary["updated"] == ["WF-A"]
    assert summary["activated"] == ["WF-A"]
    assert len(client.workflows) == 1
    assert client.workflows[0]["id"] == "wf-existing"


def test_bootstrap_workflows_creates_only_the_missing_ones_when_partially_imported(tmp_path):
    specs = _specs(tmp_path, ["WF-A", "WF-B", "WF-C"])
    client = FakeN8nClient(
        workflows=[
            {
                "id": "wf-a",
                "name": "WF-A",
                "nodes": [],
                "connections": {},
                "settings": {},
                "active": False,
                "versionId": "v1",
            }
        ]
    )

    summary = bootstrap_workflows(client, tmp_path, CREDENTIAL, specs=specs)

    assert summary["created"] == ["WF-B", "WF-C"]
    assert summary["updated"] == ["WF-A"]
    assert len(client.workflows) == 3
    assert summary["total_after"] == 3


def test_bootstrap_workflows_rerun_on_a_fully_bootstrapped_instance_never_duplicates(tmp_path):
    specs = _specs(tmp_path, ["WF-A", "WF-B"])
    client = FakeN8nClient()
    bootstrap_workflows(client, tmp_path, CREDENTIAL, specs=specs)
    first_ids = sorted(workflow["id"] for workflow in client.workflows)

    second_summary = bootstrap_workflows(client, tmp_path, CREDENTIAL, specs=specs)

    assert second_summary["created"] == []
    assert second_summary["updated"] == ["WF-A", "WF-B"]
    assert len(client.workflows) == 2
    assert sorted(workflow["id"] for workflow in client.workflows) == first_ids


def test_activate_workflow_unwraps_both_the_get_and_patch_envelopes(tmp_path):
    client = FakeN8nClient(
        workflows=[
            {
                "id": "wf-1",
                "name": "WF-A",
                "nodes": [],
                "connections": {},
                "settings": {},
                "active": False,
                "versionId": "v1",
            }
        ]
    )

    activated = activate_workflow(client, "wf-1", payload={})

    assert activated["active"] is True
    assert activated["id"] == "wf-1"


def test_get_workflows_by_name_unwraps_the_list_envelope():
    client = FakeN8nClient(
        workflows=[
            {
                "id": "wf-1",
                "name": "WF-A",
                "nodes": [],
                "connections": {},
                "settings": {},
                "active": False,
                "versionId": "v1",
            }
        ]
    )

    result = get_workflows_by_name(client)

    assert set(result) == {"WF-A"}
    assert result["WF-A"]["id"] == "wf-1"


# --- end-to-end resume scenarios (A-E) -------------------------------------


def test_scenario_a_pristine_n8n_full_bootstrap(tmp_path):
    client = FakeN8nClient(setup_needed=True, credentials=[], workflows=[])
    env = full_env()
    specs = _specs(tmp_path, ["WF-A", "WF-B"])

    owner_context = ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)
    summary = bootstrap_workflows(client, tmp_path, credential, specs=specs)

    assert owner_context["mode"] == "created"
    assert credential["created"] is True
    assert summary["created"] == ["WF-A", "WF-B"]


def test_scenario_b_owner_exists_credential_missing(tmp_path):
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="Test-Owner-Password-123!",
        credentials=[],
    )
    env = full_env()

    owner_context = ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)

    assert owner_context["mode"] == "resumed"
    assert credential["created"] is True
    assert credential["name"] == "Postgres account"


def test_scenario_c_owner_and_credential_exist_workflows_missing(tmp_path):
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="Test-Owner-Password-123!",
        credentials=[{"id": "cred-existing", "name": "Postgres account", "type": "postgres"}],
        workflows=[],
    )
    env = full_env()
    specs = _specs(tmp_path, ["WF-A", "WF-B"])

    owner_context = ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)
    summary = bootstrap_workflows(client, tmp_path, credential, specs=specs)

    assert owner_context["mode"] == "resumed"
    assert credential == {"id": "cred-existing", "name": "Postgres account", "created": False}
    assert summary["created"] == ["WF-A", "WF-B"]


def test_scenario_d_partially_imported_workflows(tmp_path):
    client = FakeN8nClient(
        setup_needed=False,
        owner={"id": "owner-1", "email": "ai5r-bootstrap@example.invalid"},
        owner_password="Test-Owner-Password-123!",
        credentials=[{"id": "cred-existing", "name": "Postgres account", "type": "postgres"}],
        workflows=[
            {
                "id": "wf-a",
                "name": "WF-A",
                "nodes": [],
                "connections": {},
                "settings": {},
                "active": True,
                "versionId": "v1",
            }
        ],
    )
    env = full_env()
    specs = _specs(tmp_path, ["WF-A", "WF-B", "WF-C"])

    owner_context = ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)
    summary = bootstrap_workflows(client, tmp_path, credential, specs=specs)

    assert owner_context["mode"] == "resumed"
    assert credential["created"] is False
    assert summary["created"] == ["WF-B", "WF-C"]
    assert summary["updated"] == ["WF-A"]
    assert summary["total_after"] == 3


def test_scenario_e_fully_bootstrapped_rerun_is_idempotent(tmp_path):
    specs = _specs(tmp_path, ["WF-A", "WF-B"])
    client = FakeN8nClient(setup_needed=True, credentials=[], workflows=[])
    env = full_env()

    # First run: full pristine bootstrap.
    ensure_owner_session(client, env)
    credential = get_or_create_postgres_credential(client, env)
    bootstrap_workflows(client, tmp_path, credential, specs=specs)
    workflow_count_after_first_run = len(client.workflows)
    credential_count_after_first_run = len(client.credentials)

    # Second run: same env, same (now-existing) n8n state.
    owner_context = ensure_owner_session(client, env)
    credential_again = get_or_create_postgres_credential(client, env)
    summary_again = bootstrap_workflows(client, tmp_path, credential_again, specs=specs)

    assert owner_context["mode"] == "resumed"
    assert credential_again["created"] is False
    assert credential_again["id"] == credential["id"]
    assert len(client.credentials) == credential_count_after_first_run
    assert summary_again["created"] == []
    assert summary_again["updated"] == ["WF-A", "WF-B"]
    assert len(client.workflows) == workflow_count_after_first_run


# --- webhookId regression: the "active=true but webhook 404" production bug ---
#
# Root cause (proven with a positive AND a negative controlled experiment
# against a real, disposable n8n 1.115.3 instance, see the mission's own
# investigation): a webhook trigger node with no `webhookId` of its own is
# registered by n8n under a synthetic, workflow-ID-prefixed compound path
# instead of its declared static production path. The workflow reports
# active=true (both via GET /rest/workflows/{id} and n8n's own startup
# log), so a naive "active=true" assertion can never catch this -- only
# checking the webhookId field itself (statically) or the real webhook
# response (live) can.


def test_load_workflow_source_rejects_a_webhook_node_with_no_webhookId(tmp_path):
    workflow = {
        "name": "WF-NO-WEBHOOKID",
        "nodes": [{"name": "Webhook", "type": WEBHOOK_NODE_TYPE, "parameters": {"path": "ltsa/x"}}],
        "connections": {},
        "settings": {},
    }
    source = tmp_path / "WF-NO-WEBHOOKID.json"
    source.write_text(json.dumps(workflow), encoding="utf-8")

    with pytest.raises(RuntimeError, match="webhookId"):
        load_workflow_source(source, CREDENTIAL)


def test_load_workflow_source_accepts_a_webhook_node_with_a_webhookId(tmp_path):
    workflow = {
        "name": "WF-WITH-WEBHOOKID",
        "nodes": [
            {"name": "Webhook", "type": WEBHOOK_NODE_TYPE, "parameters": {"path": "ltsa/x"}, "webhookId": "x-001"}
        ],
        "connections": {},
        "settings": {},
    }
    source = tmp_path / "WF-WITH-WEBHOOKID.json"
    source.write_text(json.dumps(workflow), encoding="utf-8")

    payload = load_workflow_source(source, CREDENTIAL)

    assert payload["nodes"][0]["webhookId"] == "x-001"


def test_every_real_canonical_workflow_source_has_a_webhookId_on_every_webhook_node():
    """The direct regression test for the production bug: reads the REAL
    canonical source files WORKFLOW_SPECS points to (not fixtures), and
    asserts every n8n-nodes-base.webhook node has a non-empty webhookId.
    Before the fix, this failed for exactly the 3 Postgres-backed
    workflows (seal_list, seal_stock_list, seal_pump_compatibility_list)
    -- the exact 3 that returned "webhook is not registered" in
    production -- and passed for the 2 pure-passthrough ones (pump_list,
    pump_detail), matching the observed working/failing split exactly."""
    missing = []
    for spec in WORKFLOW_SPECS:
        source_path = REPO_ROOT / spec["source"]
        workflow = json.loads(source_path.read_text(encoding="utf-8"))
        for node in workflow.get("nodes", []):
            if node.get("type") == WEBHOOK_NODE_TYPE and not node.get("webhookId"):
                missing.append(f"{spec['name']} ({source_path})")

    assert missing == []


def test_every_real_canonical_workflow_source_loads_without_a_webhookId_validation_error():
    """Complements the structural check above by also exercising the
    real load_workflow_source() pipeline (field renaming, credential
    injection) against every real canonical source file end to end --
    would fail loudly (RuntimeError) if any of the 5 regressed."""
    for spec in WORKFLOW_SPECS:
        source_path = REPO_ROOT / spec["source"]
        load_workflow_source(source_path, CREDENTIAL)  # must not raise


# --- repo root: no dependence on Path.cwd() -------------------------------
#
# Regression: bootstrap_ltsa_n8n.py used Path.cwd() as the base for every
# WORKFLOW_SPECS source path. Reproduced directly: running the real script
# from CORE-SERVICES/RUNTIME raised FileNotFoundError on a doubled-up,
# nonexistent path
# (CORE-SERVICES/RUNTIME/PRODUCTS/LTSA-BRAIN/BUILD-PACKS/...).


def test_default_repo_root_is_derived_from_this_scripts_own_location_not_cwd():
    # bootstrap_ltsa_n8n.py lives at <repo_root>/CORE-SERVICES/RUNTIME/.
    assert (DEFAULT_REPO_ROOT / "CORE-SERVICES" / "RUNTIME" / "bootstrap_ltsa_n8n.py").is_file()


def test_default_repo_root_resolves_every_real_workflow_spec_source():
    for spec in WORKFLOW_SPECS:
        assert (DEFAULT_REPO_ROOT / spec["source"]).is_file()


# --- health contract: reject a dashboard-HTML masquerade -------------------
#
# Regression: nginx's public routing table had no dedicated /health
# location, so a request for /health fell through to the dashboard SPA's
# catch-all route and returned its index.html -- HTTP 200, but not the
# real API health JSON. A bare status-code check could never catch this;
# reproduced directly against a real nginx-fronted stack before the fix.


def test_verify_runtime_marks_api_health_valid_for_the_real_health_contract(monkeypatch):
    def fake_call_json(url):
        if url.endswith("/health"):
            return 200, {"status": "OK", "version": "1.0.0", "organization": "OK", "database": "OK", "n8n": "OK"}
        return 200, {"success": True, "data": []}

    monkeypatch.setattr(bootstrap_ltsa_n8n, "call_json", fake_call_json)

    results = verify_runtime(
        {"AI5R_API_PUBLIC_URL": "http://example.test", "AI5R_N8N_PUBLIC_URL": "http://example.test"}
    )

    assert results["api_health"]["valid"] is True


def test_verify_runtime_rejects_a_dashboard_html_response_masquerading_as_health(monkeypatch):
    dashboard_html = "<!doctype html>\n<html><head><title>AI5R Dashboard</title></head></html>"

    def fake_call_json(url):
        if url.endswith("/health"):
            return 200, dashboard_html
        return 200, {"success": True, "data": []}

    monkeypatch.setattr(bootstrap_ltsa_n8n, "call_json", fake_call_json)

    results = verify_runtime(
        {"AI5R_API_PUBLIC_URL": "http://example.test", "AI5R_N8N_PUBLIC_URL": "http://example.test"}
    )

    assert results["api_health"]["status"] == 200
    assert results["api_health"]["body"] == dashboard_html
    assert results["api_health"]["valid"] is False


def test_verify_runtime_rejects_a_non_200_health_status_even_with_dict_body(monkeypatch):
    def fake_call_json(url):
        if url.endswith("/health"):
            return 503, {"status": "OK"}
        return 200, {"success": True, "data": []}

    monkeypatch.setattr(bootstrap_ltsa_n8n, "call_json", fake_call_json)

    results = verify_runtime(
        {"AI5R_API_PUBLIC_URL": "http://example.test", "AI5R_N8N_PUBLIC_URL": "http://example.test"}
    )

    assert results["api_health"]["valid"] is False


def test_verify_runtime_only_annotates_the_api_health_key_with_valid(monkeypatch):
    # Every other probe keeps its existing {"status", "body"}-only shape --
    # this is a targeted, additive fix, not a reshaping of the whole
    # verification report.
    monkeypatch.setattr(bootstrap_ltsa_n8n, "call_json", lambda url: (200, {"success": True, "data": []}))

    results = verify_runtime(
        {"AI5R_API_PUBLIC_URL": "http://example.test", "AI5R_N8N_PUBLIC_URL": "http://example.test"}
    )

    assert set(results["api_pumps"]) == {"status", "body"}
    assert set(results["n8n_pump_list"]) == {"status", "body"}
    assert set(results["api_health"]) == {"status", "body", "valid"}


# --- Postgres zero-row safety: the "HTTP 200 + empty body" production bug ---
#
# Root cause (proven against a real, disposable n8n 1.115.3 instance --
# see the mission's own investigation): a Postgres node (operation=
# "executeQuery") with no alwaysOutputData, feeding a webhook's response
# chain, produces zero output items whenever its query returns zero rows.
# n8n's execution engine does not run a downstream node when every
# upstream connection feeding it produced zero items, so the Code node
# and the Respond-to-Webhook node downstream of it never execute at all
# -- confirmed directly from a real execution's own runData, whose
# lastNodeExecuted was the Postgres node itself. n8n then falls back to
# its own default: HTTP 200 with a completely empty body, which is
# exactly what caused every gateway's json.loads() to raise
# json.decoder.JSONDecodeError: Expecting value.


def _pg_node(*, always_output_data: bool, operation: str = "executeQuery") -> dict:
    node = {
        "name": "Query",
        "type": POSTGRES_NODE_TYPE,
        "parameters": {"operation": operation, "query": "SELECT * FROM seal_registry;"},
    }
    if always_output_data:
        node["alwaysOutputData"] = True
    return node


def _webhook_node() -> dict:
    return {"name": "Webhook", "type": WEBHOOK_NODE_TYPE, "webhookId": "x-001", "parameters": {"path": "ltsa/x"}}


def test_load_workflow_source_rejects_a_postgres_query_node_with_no_alwaysOutputData(tmp_path):
    workflow = {
        "name": "WF-NO-ALWAYS-OUTPUT",
        "nodes": [_webhook_node(), _pg_node(always_output_data=False)],
        "connections": {},
        "settings": {},
    }
    source = tmp_path / "WF-NO-ALWAYS-OUTPUT.json"
    source.write_text(json.dumps(workflow), encoding="utf-8")

    with pytest.raises(RuntimeError, match="alwaysOutputData"):
        load_workflow_source(source, CREDENTIAL)


def test_load_workflow_source_accepts_a_postgres_query_node_with_alwaysOutputData(tmp_path):
    workflow = {
        "name": "WF-WITH-ALWAYS-OUTPUT",
        "nodes": [_webhook_node(), _pg_node(always_output_data=True)],
        "connections": {},
        "settings": {},
    }
    source = tmp_path / "WF-WITH-ALWAYS-OUTPUT.json"
    source.write_text(json.dumps(workflow), encoding="utf-8")

    payload = load_workflow_source(source, CREDENTIAL)

    assert payload["nodes"][1]["alwaysOutputData"] is True


def test_load_workflow_source_ignores_a_postgres_node_that_is_not_executeQuery(tmp_path):
    # A different operation (e.g. insert) is not the proven zero-row-skip
    # mechanism this validator targets -- never flagged, never guessed at.
    workflow = {
        "name": "WF-INSERT-OP",
        "nodes": [_webhook_node(), _pg_node(always_output_data=False, operation="insert")],
        "connections": {},
        "settings": {},
    }
    source = tmp_path / "WF-INSERT-OP.json"
    source.write_text(json.dumps(workflow), encoding="utf-8")

    load_workflow_source(source, CREDENTIAL)  # must not raise


def test_load_workflow_source_ignores_a_postgres_node_with_no_webhook_trigger(tmp_path):
    # No webhook trigger in this workflow at all -- this validator only
    # concerns itself with a Postgres node feeding a webhook's own
    # response chain, never postgres-only automation workflows.
    workflow = {
        "name": "WF-NO-WEBHOOK",
        "nodes": [_pg_node(always_output_data=False)],
        "connections": {},
        "settings": {},
    }
    source = tmp_path / "WF-NO-WEBHOOK.json"
    source.write_text(json.dumps(workflow), encoding="utf-8")

    load_workflow_source(source, CREDENTIAL)  # must not raise


def test_every_real_canonical_postgres_backed_workflow_source_has_alwaysOutputData():
    """The direct regression test for the production bug: reads the REAL
    canonical source files WORKFLOW_SPECS points to (not fixtures), and
    asserts every Postgres executeQuery node in a webhook-triggered
    workflow has alwaysOutputData set. Before the fix, this failed for
    exactly the 3 Postgres-backed workflows (seal_list, seal_stock_list,
    seal_pump_compatibility_list) -- the exact 3 that returned HTTP 200
    with an empty body in production."""
    missing = []
    for spec in WORKFLOW_SPECS:
        source_path = REPO_ROOT / spec["source"]
        workflow = json.loads(source_path.read_text(encoding="utf-8"))
        node_types = {node.get("type") for node in workflow.get("nodes", [])}
        if WEBHOOK_NODE_TYPE not in node_types or POSTGRES_NODE_TYPE not in node_types:
            continue
        for node in workflow.get("nodes", []):
            if node.get("type") != POSTGRES_NODE_TYPE:
                continue
            if node.get("parameters", {}).get("operation") != "executeQuery":
                continue
            if not node.get("alwaysOutputData"):
                missing.append(f"{spec['name']} ({source_path})")

    assert missing == []


def test_every_real_canonical_workflow_source_still_loads_without_error():
    for spec in WORKFLOW_SPECS:
        source_path = REPO_ROOT / spec["source"]
        load_workflow_source(source_path, CREDENTIAL)  # must not raise
