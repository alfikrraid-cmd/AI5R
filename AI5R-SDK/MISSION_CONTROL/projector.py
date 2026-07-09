from MISSION_CONTROL.read_model import MissionControlReadModel


class MissionControlProjector:

    def __init__(self):

        self.model = MissionControlReadModel()

    def project(self, event: dict):

        event_type = event["event_type"]

        payload = event["payload"]

        if event_type == "EMPLOYEE_ACTIVITY_RECORDED":

            self.model.organization.append({

                "employee_id": payload["employee_id"],

                "status": payload["status"],

                "progress": payload["progress"],

                "activity": payload["activity_type"],

            })

            self.model.timeline.append(payload)

        return self.model
