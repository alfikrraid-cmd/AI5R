from __future__ import annotations


class BootSimulation:
    def __init__(self):
        self.state = {
            "os": False,
            "employee": False,
            "memory": False,
            "knowledge": False,
            "agent": False,
            "message": False,
            "skill": False,
            "performance": False,
            "shutdown": False,
            "reload": False,
        }

    def boot_os(self):
        self.state["os"] = True

    def init_employee(self):
        self.state["employee"] = True

    def init_memory(self):
        self.state["memory"] = True

    def init_knowledge(self):
        self.state["knowledge"] = True

    def spawn_agent(self):
        self.state["agent"] = True

    def send_message(self):
        self.state["message"] = True

    def update_skill(self):
        self.state["skill"] = True

    def update_performance(self):
        self.state["performance"] = True

    def shutdown(self):
        self.state["shutdown"] = True

    def reload(self):
        self.state["reload"] = True

    def snapshot(self):
        return dict(self.state)
