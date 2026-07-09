from dataclasses import dataclass, field


@dataclass(slots=True)
class Executive:

    executive_id: str

    name: str

    title: str

    department: str

    responsibilities: list[str] = field(default_factory=list)

    motto: str = ""

    status: str = "READY"

    def assign_mission(self, mission: str):

        self.status = "WORKING"

        return {

            "executive": self.name,

            "mission": mission,

            "status": self.status,

        }

    def complete(self):

        self.status = "READY"

