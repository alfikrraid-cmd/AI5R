from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from RUNTIME.SCALING import AgentPool, LoadBalancer


def test_agent_pool():
    pool = AgentPool()

    pool.submit("A", lambda: 1)
    pool.submit("B", lambda: 2)

    result = pool.run()

    assert result["A"] == 1
    assert result["B"] == 2


def test_load_balancer():
    lb = LoadBalancer()

    workers = ["W1", "W2", "W3"]

    assert lb.next_worker(workers) == "W1"
    assert lb.next_worker(workers) == "W2"
    assert lb.next_worker(workers) == "W3"
