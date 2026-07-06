from POSITION.position_engine import PositionEngine


class PositionRuntime:

    def __init__(self):
        self.engine = PositionEngine()
        self._positions = {}

    def register(self, position):

        result = self.engine.build(position)

        self._positions[position.position_id] = result

        return {
            "status": "REGISTERED",
            "position_id": position.position_id,
        }

    def get(self, position_id):
        return self._positions.get(position_id)

    def list_all(self):
        return list(self._positions.values())

    def list_by_department(self, department):
        return [
            x
            for x in self._positions.values()
            if x["position"].department == department
        ]

    def list_by_authority(self, minimum_level):
        return [
            x
            for x in self._positions.values()
            if x["position"].authority_level >= minimum_level
        ]
