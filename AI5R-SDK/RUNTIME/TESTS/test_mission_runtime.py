import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from RUNTIME.enterprise_mission import EnterpriseMission
from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.enterprise_worker import EnterpriseWorker
from RUNTIME.mission_runtime import MissionRuntime


class TestWorker(EnterpriseWorker):
    def execute(self, task):
        return {
            "status": "success",
            "task_type": task.task_type,
            "worker_id": self.worker_id,
        }


def test_mission_runtime():
    mission = EnterpriseMission(
        mission_type="ltsa_pump_report_analysis",
        title="Analyze Pump Report",
        objective="Generate recommendation and work order",
        source_object_id="warehouse-report-001",
        customer_id="customer-001",
    )

    task = EnterpriseTask(
        task_type="search_knowledge",
        title="Search Knowledge",
        instruction="Find relevant pump maintenance knowledge",
        mission_id=mission.mission_id,
    )

    worker = TestWorker(
        worker_type="knowledge",
        name="Knowledge Worker",
        capabilities=["search_knowledge"],
    )

    runtime = MissionRuntime()
    runtime.register_worker(worker)
    runtime.load_tasks([task])

    report = runtime.run(mission)

    assert report["mission"]["status"] == "completed"
    assert report["results"][0]["task"]["status"] == "completed"
    assert report["results"][0]["result"]["status"] == "success"


if __name__ == "__main__":
    test_mission_runtime()
    print("EP-006 Mission Runtime OK")
