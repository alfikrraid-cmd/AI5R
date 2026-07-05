class OrganizationObject:
    def __init__(self, object_id, name, object_type, parent_id=None):
        self.object_id = object_id
        self.name = name
        self.object_type = object_type
        self.parent_id = parent_id

    def to_dict(self):
        return {
            "object_id": self.object_id,
            "name": self.name,
            "object_type": self.object_type,
            "parent_id": self.parent_id,
        }
