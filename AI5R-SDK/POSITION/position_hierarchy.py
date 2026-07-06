class PositionHierarchy:

    def __init__(self):
        self._nodes = {}

    def add(self, position):
        self._nodes[position.position_id] = position

        return {
            "status": "ADDED",
            "position_id": position.position_id,
        }

    def get_manager(self, position):
        if not position.reports_to:
            return None

        return self._nodes.get(position.reports_to)

    def get_direct_reports(self, position):
        return [
            x
            for x in self._nodes.values()
            if x.reports_to == position.position_id
        ]

    def get_chain_of_command(self, position):
        chain = []
        current = position

        while current.reports_to:
            manager = self._nodes.get(current.reports_to)

            if manager is None:
                break

            chain.append(manager)
            current = manager

        return chain
