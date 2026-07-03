import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MISSION.task_planner import TaskPlanner
from RUNTIME.enterprise_mission import EnterpriseMission


def test_task_planner():

    mission = EnterpriseMission(
        mission_type="ltsa_pump_report_analysis",
        title="Analyze Pump",
        objective="Analyze uploaded pump report",
    )

    planner = TaskPlanner()

    tasks = planner.plan(mission)

    assert len(tasks) == 5

    assert tasks[0].task_type == "extract_pump_findings"
    assert tasks[4].task_type == "generate_pdf_report"


if __name__ == "__main__":
    test_task_planner()
    print("LTSA-002 Task Planner OK")
