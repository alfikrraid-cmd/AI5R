from RUNTIME.enterprise_mission import EnterpriseMission
from RUNTIME.enterprise_task import EnterpriseTask


class MissionBuilder:

    def build(self, warehouse_object):

        mission = EnterpriseMission(
            mission_type="ltsa_pump_report_analysis",
            title="Analyze Pump Report",
            objective="Generate diagnosis, recommendation, work order and report",
            source_object_id=warehouse_object["object_id"],
            customer_id=warehouse_object.get("customer_id"),
        )

        tasks = [

            EnterpriseTask(
                task_type="extract_pump_findings",
                title="Extract Pump Findings",
                instruction="Extract all findings from report",
                mission_id=mission.mission_id,
            ),

            EnterpriseTask(
                task_type="search_knowledge",
                title="Search Knowledge",
                instruction="Find relevant maintenance knowledge",
                mission_id=mission.mission_id,
            ),

            EnterpriseTask(
                task_type="generate_recommendation",
                title="Generate Recommendation",
                instruction="Generate maintenance recommendation",
                mission_id=mission.mission_id,
            ),

            EnterpriseTask(
                task_type="generate_work_order",
                title="Generate Work Order",
                instruction="Generate work order",
                mission_id=mission.mission_id,
            ),

            EnterpriseTask(
                task_type="generate_pdf_report",
                title="Generate PDF Report",
                instruction="Generate final PDF report",
                mission_id=mission.mission_id,
            ),
        ]

        return mission, tasks
