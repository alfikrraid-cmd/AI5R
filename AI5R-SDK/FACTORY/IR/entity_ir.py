"""
AI5R Entity IR
FM-004.5
"""


class EntityIR:

    def __init__(self, name, fields=None):
        self.name = name
        self.fields = fields or []

    def to_dict(self):
        return {
            "kind": "entity",
            "name": self.name,
            "fields": self.fields
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            fields=data.get("fields", [])
        )
