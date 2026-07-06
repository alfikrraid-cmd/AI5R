from dataclasses import dataclass


@dataclass
class EmployeeContext:
    mission: str = ""
    vision: str = ""
    current_project: str = ""
    current_goal: str = ""
    current_kpi: str = ""
