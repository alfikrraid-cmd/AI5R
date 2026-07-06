from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DemoEvent:
    actor: str
    action: str
    target: str | None = None
    data: dict | None = None


class DemoRuntime:
    def __init__(self):
        self.events: list[DemoEvent] = []
        self.state: dict = {
            "employees": {},
            "tasks": {},
            "memory": [],
            "skills": {},
            "performance": {},
        }

    def spawn_employee(self, emp_id: str):
        self.state["employees"][emp_id] = {"active": True}
        self.events.append(DemoEvent(emp_id, "SPAWN_EMPLOYEE"))

    def assign_task(self, emp_id: str, task: str):
        self.state["tasks"][task] = emp_id
        self.events.append(DemoEvent(emp_id, "ASSIGN_TASK", task))

    def write_memory(self, emp_id: str, content: dict):
        self.state["memory"].append({"emp": emp_id, "content": content})
        self.events.append(DemoEvent(emp_id, "WRITE_MEMORY", data=content))

    def improve_skill(self, emp_id: str, skill: str):
        self.state["skills"].setdefault(emp_id, {})
        self.state["skills"][emp_id][skill] = (
            self.state["skills"][emp_id].get(skill, 0) + 1
        )
        self.events.append(DemoEvent(emp_id, "IMPROVE_SKILL", skill))

    def evaluate(self, emp_id: str):
        self.state["performance"][emp_id] = "OK"
        self.events.append(DemoEvent(emp_id, "EVALUATE"))

    def snapshot(self):
        return {
            "events": len(self.events),
            "state": self.state,
        }
