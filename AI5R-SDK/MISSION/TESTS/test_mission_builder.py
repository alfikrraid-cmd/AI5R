import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from MISSION.mission_builder import MissionBuilder


def test_builder():

    warehouse = {
        "object_id": "warehouse-001",
        "customer_id": "customer-001",
    }

    builder = MissionBuilder()

    mission, tasks = builder.build(warehouse)

    assert mission.mission_type == "ltsa_pump_report_analysis"

    assert len(tasks) == 5

    assert tasks[0].task_type == "extract_pump_findings"

    assert tasks[4].task_type == "generate_pdf_report"


if __name__ == "__main__":
    test_builder()
    print("LTSA-001 Mission Builder OK")
