from typing import List

from RUNTIME.enterprise_task import EnterpriseTask
from RUNTIME.enterprise_mission import EnterpriseMission


class TaskPlanner:

    def plan(self, mission: EnterpriseMission) -> List[EnterpriseTask]:

        tasks = []

        if mission.mission_type == "ltsa_pump_report_analysis":

            task_specs = [
                ("extract_pump_findings", "Extract Pump Findings"),
                ("search_knowledge", "Search Knowledge"),
                ("generate_recommendation", "Generate Recommendation"),
                ("generate_work_order", "Generate Work Order"),
                ("generate_pdf_report", "Generate PDF Report"),
            ]

            for task_type, title in task_specs:

                tasks.append(
                    EnterpriseTask(
                        task_type=task_type,
                        title=title,
                        instruction=title,
                        mission_id=mission.mission_id,
                    )
                )

        return tasks
