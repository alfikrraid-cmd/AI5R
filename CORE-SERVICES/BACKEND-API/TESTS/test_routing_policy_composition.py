import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "AI5R-SDK"))

import pytest

import dependencies
from AI_RUNTIME.ROUTER.routing_policy import RoutingMode, RoutingPolicyError


def _mode(monkeypatch, value):
    for k in ("AI5R_DAHONO_API_KEY", "AI5R_DAHONO_MODEL", "AI5R_CLAUDE_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    if value is None:
        monkeypatch.delenv("AI5R_ROUTING_POLICY", raising=False)
    else:
        monkeypatch.setenv("AI5R_ROUTING_POLICY", value)
    client = dependencies._build_copilot_ai_client()
    return client._router.provider_selector._routing_policy.mode


def test_missing_env_is_auto(monkeypatch):
    assert _mode(monkeypatch, None) is RoutingMode.AUTO


def test_env_selects_mode(monkeypatch):
    assert _mode(monkeypatch, "LOCAL_FIRST") is RoutingMode.LOCAL_FIRST


def test_invalid_env_raises_on_composition(monkeypatch):
    with pytest.raises(RoutingPolicyError):
        _mode(monkeypatch, "COST_OPTIMIZED")
