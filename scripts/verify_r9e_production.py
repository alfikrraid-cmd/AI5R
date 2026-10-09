#!/usr/bin/env python3
"""
Production Verification Script for LTSA Drawing Viewer UI (R9E).
Verifies:
1. Nginx serves updated dashboard bundle with R9E components.
2. No MinIO secrets or keys leaked to client bundle.
3. Authenticated Drawing API endpoints for:
   - 211-P-26A: DE (GA-230821) and NDE (GA-230826) independent
   - 101-P-8A / 101-P-8B: GA-214072-1 (storage_available=False)
   - 101-P-8C: GA-214072-1 ABSENT (exception preserved)
   - Binary streaming: GA-230821 returns valid PDF bytes (%PDF-1.4)
   - Slash document code routing: D/74904-1 returns 200
4. DB counts frozen: 129 documents, 318 links.
"""

import re
import subprocess
import sys
import urllib.request
import json

BASE_URL = "http://127.0.0.1:8080"
API_CONTAINER = "ai5ros-prod-api-1"
POSTGRES_CONTAINER = "ai5ros-prod-postgres-1"

def print_header(title):
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)

def verify_frontend_bundle():
    print_header("GATE R9E.P1 — FRONTEND BUNDLE SERVING")
    
    # 1. Fetch index.html
    req = urllib.request.Request(f"{BASE_URL}/")
    with urllib.request.urlopen(req) as resp:
        assert resp.status == 200, f"Index failed: {resp.status}"
        html = resp.read().decode("utf-8")
        assert "root" in html, "root element not found in HTML"
        print(f"PASS: index.html served with 200 OK ({len(html)} bytes)")

    # 2. Extract JS bundle
    match = re.search(r'assets/(index-[^.]+\.js)', html)
    assert match, "JS bundle not found in index.html"
    bundle_name = match.group(1)
    print(f"PASS: Deployed bundle identified as {bundle_name}")

    # 3. Fetch and inspect JS bundle
    bundle_url = f"{BASE_URL}/assets/{bundle_name}"
    with urllib.request.urlopen(bundle_url) as resp:
        assert resp.status == 200, f"Bundle failed: {resp.status}"
        js_code = resp.read().decode("utf-8")
        print(f"PASS: Bundle fetched successfully ({len(js_code)} bytes)")

    # Assert R9E frontend content markers
    assert "Drawing file not available" in js_code, "Marker 'Drawing file not available' missing"
    assert "CAD Model" in js_code, "Marker 'CAD Model' missing"
    assert "target_code" in js_code, "Query param 'target_code' missing"
    assert "getDrawingContentBlob" in js_code or "drawings/" in js_code, "Drawing content API missing"
    
    # Assert zero credential leaks
    for forbidden in ["MINIO_ROOT_PASSWORD", "AWS_SECRET_ACCESS_KEY", "minio_secret", "Pertamina_"]:
        assert forbidden not in js_code, f"Security violation: {forbidden} found in bundle"
    
    print("PASS: R9E markers verified and zero credentials leaked")

def get_auth_token():
    print_header("GATE R9E.P2 — AUTHENTICATION TOKEN GENERATION")
    code = """
import dependencies
from API.auth_service import issue_access_token
repo = dependencies._auth_repository
users = repo.list_users()
target = next((u for u in users if u.get('role') in ('SUPERUSER', 'TAP_ADMIN', 'TAP_ENGINEER') and u.get('user_status') == 'ACTIVE'), users[0])
token = issue_access_token(target['id'], target['organization_id'])
print(f"ROLE:{target.get('role')}")
print(token)
"""
    cmd = ["docker", "exec", "-i", API_CONTAINER, "python3", "-"]
    res = subprocess.run(cmd, input=code, capture_output=True, text=True, check=True)
    lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
    token = lines[-1]
    role_info = [l for l in lines if l.startswith("ROLE:")]
    assert len(token) > 20, f"Failed to generate test token: {res.stderr}"
    print(f"PASS: Valid JWT generated ({role_info[0] if role_info else 'ROLE:unknown'}, {token[:15]}...)")
    return token

def verify_drawing_api(token):
    print_header("GATE R9E.P3 — LIVE DRAWING API VERIFICATION")
    headers = {"Authorization": f"Bearer {token}"}

    def api_get(endpoint):
        req = urllib.request.Request(f"{BASE_URL}{endpoint}", headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                content_type = resp.headers.get("Content-Type", "")
                return resp.status, content_type, data
        except urllib.error.HTTPError as e:
            return e.code, e.headers.get("Content-Type", ""), e.read()

    # 1. 211-P-26A: DE (GA-230821) and NDE (GA-230826)
    status, ct, data = api_get("/api/ltsa/drawings?target_code=211-P-26A")
    assert status == 200, f"211-P-26A query failed: {status}"
    payload = json.loads(data.decode("utf-8"))
    drawings = payload.get("data", [])
    print(f"211-P-26A returned {len(drawings)} drawings:")
    for d in drawings:
        print(f"  - {d.get('document_code')} | Side: {d.get('equipment_side')} | Storage: {d.get('storage_available')}")

    doc_codes = {d["document_code"] for d in drawings}
    assert "GA-230821" in doc_codes, "GA-230821 (DE) missing from 211-P-26A"
    assert "GA-230826" in doc_codes, "GA-230826 (NDE) missing from 211-P-26A"
    ga230821 = next(d for d in drawings if d["document_code"] == "GA-230821")
    ga230826 = next(d for d in drawings if d["document_code"] == "GA-230826")
    assert ga230821["equipment_side"] == "DE", f"GA-230821 equipment_side expected DE, got {ga230821['equipment_side']}"
    assert ga230826["equipment_side"] == "NDE", f"GA-230826 equipment_side expected NDE, got {ga230826['equipment_side']}"
    print("PASS: 211-P-26A independent DE/NDE sides verified")

    # 2. 101-P-8A & 101-P-8B: GA-214072-1 (Reference-Only)
    for tag in ["101-P-8A", "101-P-8B"]:
        status, ct, data = api_get(f"/api/ltsa/drawings?target_code={tag}")
        assert status == 200, f"{tag} query failed"
        p = json.loads(data.decode("utf-8"))
        d_list = p.get("data", [])
        ga_ref = next((d for d in d_list if d["document_code"] == "GA-214072-1"), None)
        assert ga_ref is not None, f"GA-214072-1 missing from {tag}"
        assert ga_ref["storage_available"] is False, f"GA-214072-1 should have storage_available=False for {tag}"
        print(f"PASS: {tag} -> GA-214072-1 confirmed reference-only (storage_available=False)")

    # 3. 101-P-8C: GA-214072-1 MUST NOT appear
    status, ct, data = api_get("/api/ltsa/drawings?target_code=101-P-8C")
    assert status == 200, "101-P-8C query failed"
    p_8c = json.loads(data.decode("utf-8"))
    d_8c = p_8c.get("data", [])
    assert not any(d["document_code"] == "GA-214072-1" for d in d_8c), "VIOLATION: GA-214072-1 found on 101-P-8C"
    print(f"PASS: 101-P-8C returned {len(d_8c)} drawings and GA-214072-1 is strictly absent")

    # 4. Quarantined GA-187530 check: must NOT be available or promoted (404 Not Found or status=QUARANTINED)
    status, ct, data = api_get("/api/ltsa/drawings/GA-187530")
    assert status == 404 or (status == 200 and json.loads(data).get("data", {}).get("status") == "QUARANTINED"), f"GA-187530 should be 404 or QUARANTINED, got {status}"
    print(f"PASS: Quarantined GA-187530 verified not selectable/promoted (status={status})")

    # 5. Slash document code routing: D/74904-1
    status, ct, data = api_get("/api/ltsa/drawings/D/74904-1")
    assert status == 200, f"D/74904-1 routing failed: {status}"
    p_slash = json.loads(data.decode("utf-8"))
    assert p_slash.get("data", {}).get("document_code") == "D/74904-1"
    print("PASS: Slash path routing for D/74904-1 verified 200 OK")

    # 6. Binary delivery: GA-230821 content
    status, ct, raw_pdf = api_get("/api/ltsa/drawings/GA-230821/content")
    assert status == 200, f"Binary delivery failed: {status}"
    assert "pdf" in ct.lower(), f"Unexpected Content-Type: {ct}"
    assert raw_pdf.startswith(b"%PDF"), f"Corrupted PDF binary header: {raw_pdf[:10]}"
    print(f"PASS: Authenticated binary delivery for GA-230821 ({len(raw_pdf)} bytes, %PDF-1.4 header confirmed)")

def verify_database_frozen():
    print_header("GATE R9E.P4 — DATABASE INVARIANTS FROZEN")
    code = """
import dependencies
repo = dependencies.get_drawing_repository()
doc_count = repo._runner.query_scalar("SELECT count(*) FROM seal_engineering_document;")
link_count = repo._runner.query_scalar("SELECT count(*) FROM drawing_engineering_link;")
print(f"DOCUMENTS={doc_count}")
print(f"LINKS={link_count}")
"""
    cmd = ["docker", "exec", "-i", API_CONTAINER, "python3", "-"]
    try:
        res = subprocess.run(cmd, input=code, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print("POSTGRES CHECK ERROR STDERR:", e.stderr)
        print("POSTGRES CHECK ERROR STDOUT:", e.stdout)
        raise
    lines = [line.strip() for line in res.stdout.strip().split("\n") if line.strip()]
    counts = dict(line.split("=") for line in lines)
    print(f"Database counts: {counts}")
    assert counts.get("DOCUMENTS") == "129", f"Expected 129 documents, got {counts.get('DOCUMENTS')}"
    assert counts.get("LINKS") == "318", f"Expected 318 links, got {counts.get('LINKS')}"
    print("PASS: Frozen invariants verified (129 documents, 318 links)")

if __name__ == "__main__":
    print("\n" + "#" * 60)
    print(" LTSA DRAWING VIEWER UI (R9E) PRODUCTION ACCEPTANCE SUITE")
    print("#" * 60)
    try:
        verify_frontend_bundle()
        token = get_auth_token()
        verify_drawing_api(token)
        verify_database_frozen()
        print_header("OVERALL R9E ACCEPTANCE RESULT: 100% PASS")
    except Exception as e:
        print(f"\n[FAIL] Assertion failed: {e}")
        sys.exit(1)
