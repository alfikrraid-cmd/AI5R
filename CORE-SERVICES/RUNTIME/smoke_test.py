from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request
from pathlib import Path

from ops_common import DEFAULT_ENV_FILE, load_environment, validate_environment


def check(name: str, url: str, timeout: int) -> bool:
    request = urllib.request.Request(url, headers={"Accept": "application/json,text/html,*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            headers = {key.lower(): value for key, value in response.headers.items()}
    except urllib.error.URLError as error:
        print(f"[FAIL] {name}: {error}")
        return False

    ok = 200 <= status < 400
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: HTTP {status} {url}")
    for header in ("strict-transport-security", "x-content-type-options", "x-frame-options", "cache-control"):
        if header in headers:
            print(f"[PASS] {name}: {header}: {headers[header]}")
    return ok


def main() -> int:
    parser = argparse.ArgumentParser(description="AI5ROS production smoke test through the public gateway.")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE)
    parser.add_argument("--base-url", default=None, help="Override AI5R_NGINX_PUBLIC_URL for cutover testing.")
    args = parser.parse_args()

    config = load_environment(args.env_file)
    validation = validate_environment(config)
    if not validation.ok:
        for error in validation.errors:
            print(f"[FAIL] {error}")
        return 1

    timeout = int(config.get("AI5R_HEALTH_TIMEOUT_SECONDS", "10"))
    base_url = (args.base_url or config["AI5R_NGINX_PUBLIC_URL"]).rstrip("/")
    checks = (
        check("gateway-health", f"{base_url}/healthz", timeout),
        check("dashboard", base_url, timeout),
        check("api-pumps", f"{base_url}/api/ltsa/pumps", timeout),
    )

    if all(checks):
        print("[PASS] production smoke test passed")
        return 0
    print("[FAIL] production smoke test failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())