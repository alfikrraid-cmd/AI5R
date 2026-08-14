import re
import sys
from pathlib import Path
from urllib.parse import urlparse

RUNTIME_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
for path in (RUNTIME_DIR, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from bootstrap_ltsa_n8n import WORKFLOW_SPECS
from ops_common import parse_env_file
from test_runtime_compose import render_compose_with_example_env


NGINX_CONF = (RUNTIME_DIR / "docker" / "nginx-proxy.conf").read_text(encoding="utf-8").replace("\r\n", "\n")


def location_block(selector: str) -> str:
    match = re.search(rf"location\s+{re.escape(selector)}\s*\{{(?P<body>.*?)\n    \}}", NGINX_CONF, re.S)
    assert match, f"Missing nginx location {selector}"
    return match.group("body")


def assert_proxy(selector: str, upstream: str) -> None:
    block = location_block(selector)
    assert f"proxy_pass {upstream};" in block


def test_bootstrap_n8n_rest_requests_route_to_n8n_not_dashboard():
    block = location_block("/rest/")

    assert "proxy_pass http://n8n:5678;" in block
    assert "proxy_pass http://dashboard:80;" not in block
    assert "proxy_pass http://api:8000;" not in block


def test_ltsa_webhook_paths_route_to_n8n():
    assert_proxy("/webhook/", "http://n8n:5678")
    assert all(spec["webhook_path"].startswith("ltsa/") for spec in WORKFLOW_SPECS)


def test_ai5r_api_routes_still_route_to_api():
    block = location_block("/api/")

    assert "proxy_pass http://api:8000;" in block
    assert "proxy_pass http://n8n:5678;" not in block
    assert "proxy_pass http://dashboard:80;" not in block


def test_dashboard_fallback_still_routes_to_dashboard():
    block = location_block("/")

    assert "proxy_pass http://dashboard:80;" in block
    assert "proxy_pass http://n8n:5678;" not in block
    assert "proxy_pass http://api:8000;" not in block


def test_example_public_urls_share_the_same_edge_host_by_path():
    for env_file, expected_host in ((".env.example", "localhost:8080"), (".env.production.example", "osa-system.com")):
        env = parse_env_file(RUNTIME_DIR / env_file)

        assert urlparse(env["AI5R_DASHBOARD_PUBLIC_URL"]).netloc == expected_host
        assert urlparse(env["AI5R_API_PUBLIC_URL"]).netloc == expected_host
        assert urlparse(env["AI5R_N8N_PUBLIC_URL"]).netloc == expected_host


def test_compose_nginx_depends_on_every_edge_upstream_it_routes():
    compose = render_compose_with_example_env()

    assert set(compose["services"]["nginx"]["depends_on"]) >= {"dashboard", "api", "n8n"}
    assert "edge" in compose["services"]["n8n"]["networks"]