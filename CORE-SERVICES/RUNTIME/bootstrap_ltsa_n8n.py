from __future__ import annotations

import argparse
import json
import os
import secrets
import string
import sys
import urllib.error
import urllib.parse
import urllib.request
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any


WORKFLOW_SPECS = [
    {
        "key": "pump_list",
        "source": Path("PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-LIST-001.json"),
        "name": "WF-LTSA-BRAIN-PUMP-LIST-001",
        "method": "GET",
        "webhook_path": "ltsa/pump/list",
    },
    {
        "key": "pump_detail",
        "source": Path("PRODUCTS/LTSA-BRAIN/BUILD-PACKS/BP-PUMP/WORKFLOWS/WF-LTSA-BRAIN-PUMP-DETAIL-001.json"),
        "name": "WF-LTSA-BRAIN-PUMP-DETAIL-001",
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


def random_password() -> str:
    alphabet = string.ascii_letters + string.digits
    return f"AI5R-{''.join(secrets.choice(alphabet) for _ in range(18))}!9a"


def ensure_owner_session(client: N8nClient) -> dict[str, Any]:
    status, _, settings = client.request("/rest/settings", authenticated=False)
    if status != 200 or not isinstance(settings, dict):
        raise RuntimeError(f"Unable to read n8n settings: {status} {settings}")

    setup_needed = bool(settings["data"]["userManagement"]["showSetupOnFirstLoad"])
    owner_context = {
        "showSetupOnFirstLoad": setup_needed,
        "owner_setup_executed": False,
    }
    if not setup_needed:
        raise RuntimeError(
            "n8n owner setup is already completed, but no authenticated session is available. "
            "This bootstrap utility only supports the current first-load runtime state."
        )

    payload = {
        "email": "ai5r-bootstrap@example.invalid",
        "firstName": "AI5R",
        "lastName": "Bootstrap",
        "password": random_password(),
    }
    status, _, body = client.request("/rest/owner/setup", method="POST", payload=payload, authenticated=False)
    if status != 200:
        raise RuntimeError(f"Owner setup failed: {status} {body}")
    if not client.cookie_header:
        raise RuntimeError("Owner setup succeeded but no auth cookie was issued by n8n.")

    owner_context["owner_setup_executed"] = True
    owner_context["owner_id"] = body.get("id") if isinstance(body, dict) else None
    return owner_context


def get_or_create_postgres_credential(client: N8nClient, env: dict[str, str]) -> dict[str, Any]:
    status, _, credentials = client.request("/rest/credentials")
    if status != 200:
        raise RuntimeError(f"Unable to list n8n credentials: {status} {credentials}")
    if isinstance(credentials, dict):
        credentials = credentials.get("data", [])
    if not isinstance(credentials, list):
        raise RuntimeError(f"Unexpected n8n credentials payload: {credentials}")

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
    if status != 200 or not isinstance(created, dict):
        raise RuntimeError(f"Unable to create Postgres credential: {status} {created}")
    return {"id": created["id"], "name": created["name"], "created": True}


def load_workflow_source(source: Path, credential: dict[str, Any]) -> dict[str, Any]:
    workflow = json.loads(source.read_text(encoding="utf-8"))
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
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"Unable to list n8n workflows: {status} {payload}")
    return {workflow["name"]: workflow for workflow in payload.get("data", [])}


def activate_workflow(client: N8nClient, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    status, _, current = client.request(f"/rest/workflows/{workflow_id}")
    if status != 200 or not isinstance(current, dict):
        raise RuntimeError(f"Unable to load workflow {workflow_id} for activation: {status} {current}")

    activation_payload = {
        "name": current["name"],
        "nodes": current["nodes"],
        "connections": current["connections"],
        "settings": current.get("settings") or {},
        "active": True,
        "versionId": current.get("versionId"),
    }
    status, _, activated = client.request(
        f"/rest/workflows/{workflow_id}",
        method="PATCH",
        payload=activation_payload,
    )
    if status != 200 or not isinstance(activated, dict):
        raise RuntimeError(f"Unable to activate workflow {workflow_id}: {status} {activated}")
    return activated


def bootstrap_workflows(client: N8nClient, root: Path, credential: dict[str, Any]) -> dict[str, Any]:
    existing_by_name = get_workflows_by_name(client)
    summary = {
        "created": [],
        "updated": [],
        "activated": [],
        "unchanged": [],
    }

    for spec in WORKFLOW_SPECS:
        source_path = root / spec["source"]
        payload = load_workflow_source(source_path, credential)
        existing = existing_by_name.get(spec["name"])

        if existing is None:
            status, _, created = client.request("/rest/workflows", method="POST", payload=payload)
            if status != 200 or not isinstance(created, dict):
                raise RuntimeError(f"Unable to create workflow {spec['name']}: {status} {created}")
            workflow_id = created["id"]
            summary["created"].append(spec["name"])
        else:
            workflow_id = existing["id"]
            status, _, updated = client.request(f"/rest/workflows/{workflow_id}", method="PATCH", payload=payload)
            if status != 200 or not isinstance(updated, dict):
                raise RuntimeError(f"Unable to update workflow {spec['name']}: {status} {updated}")
            summary["updated"].append(spec["name"])

        activated = activate_workflow(client, workflow_id, payload)
        if activated.get("active"):
            summary["activated"].append(spec["name"])

    after = get_workflows_by_name(client)
    summary["total_after"] = len(after)
    return summary


def call_json(url: str) -> tuple[int, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body)
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8")
        try:
            return error.code, json.loads(body)
        except json.JSONDecodeError:
            return error.code, body


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
        results[key] = {"status": status, "body": body}
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = Path.cwd()
    env = parse_env_file(Path(args.env_file))
    client = N8nClient(env["AI5R_N8N_PUBLIC_URL"])

    owner_context = ensure_owner_session(client)
    credential = get_or_create_postgres_credential(client, env)
    first = bootstrap_workflows(client, root, credential)
    verification = verify_runtime(env)
    second = bootstrap_workflows(client, root, credential)

    report = {
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

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
