from .executive import Executive


class ExecutiveBoard:

    def __init__(self):

        self.executives = {}

    def register(self, executive: Executive):

        self.executives[
            executive.executive_id
        ] = executive

    def get(self, executive_id: str):

        return self.executives[executive_id]

    def all(self):

        return list(self.executives.values())
