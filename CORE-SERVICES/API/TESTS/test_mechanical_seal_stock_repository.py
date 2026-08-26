import json
from pathlib import Path
import sys

CORE_SERVICES = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES))

from API.mechanical_seal_stock_repository import MechanicalSealStockRepository, can_view_gpn


class FakeRunner:
    def __init__(self):
        self.calls = []
        self.responses = [
            json.dumps([{"stock_pool_id": "MSSP-1", "complete_seal_gpn": None}]),
            json.dumps([{"total": 1, "total_quantity": 3}]),
        ]

    def query_scalar(self, sql):
        self.calls.append(sql)
        return self.responses.pop(0)


def test_list_pools_is_paginated_and_redacts_gpn_by_default():
    runner = FakeRunner()
    result = MechanicalSealStockRepository(runner).list_pools(limit=25, offset=50)

    assert result["items"][0]["complete_seal_gpn"] is None
    assert result["total"] == 1
    assert result["total_quantity"] == 3
    assert "LIMIT 25 OFFSET 50" in runner.calls[0]
    assert "p.complete_seal_gpn" not in runner.calls[0]
    assert "NULL AS complete_seal_gpn" in runner.calls[0]


def test_internal_gpn_roles_are_explicit_and_no_parallel_role_is_created():
    assert can_view_gpn("SUPERUSER") is True
    assert can_view_gpn("JOHN_CRANE_ENGINEER") is True
    assert can_view_gpn("PERTAMINA_ENGINEER") is False
    assert can_view_gpn("PERTAMINA_VIEWER") is False
