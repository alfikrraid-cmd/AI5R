class OrganizationRegistry:
    def __init__(self):
        self.objects = {}

    def register(self, organization_object):
        self.objects[organization_object.object_id] = organization_object
        return organization_object

    def get(self, object_id):
        return self.objects.get(object_id)

    def list_all(self):
        return list(self.objects.values())

    def children_of(self, parent_id):
        return [
            obj for obj in self.objects.values()
            if obj.parent_id == parent_id
        ]
