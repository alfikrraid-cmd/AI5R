from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AI5RKernel:
    version: str = "1.0-alpha"
    status: str = "STOPPED"
    boot_time: str | None = None

    subsystems: dict = field(default_factory=dict)

    def register(self, name, subsystem):
        self.subsystems[name] = subsystem

    def boot(self):
        self.status = "RUNNING"
        self.boot_time = datetime.now(timezone.utc).isoformat()
        return self

    def shutdown(self):
        self.status = "STOPPED"
        return self

    def is_running(self):
        return self.status == "RUNNING"
