import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_worker import EnterpriseWorker


def test_worker():

    worker = EnterpriseWorker(
        worker_type="knowledge",
        name="Knowledge Worker",
        capabilities=[
            "search_knowledge",
            "classify_issue",
        ],
    )

    obj = worker.to_enterprise_object()

    assert obj["object_type"] == "enterprise_worker"
    assert obj["worker_type"] == "knowledge"

    assert worker.supports("search_knowledge")
    assert not worker.supports("generate_pdf")


if __name__ == "__main__":
    test_worker()
    print("EP-005.5 Enterprise Worker OK")
