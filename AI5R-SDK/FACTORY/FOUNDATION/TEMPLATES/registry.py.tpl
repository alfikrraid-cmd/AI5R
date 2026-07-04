class {{ class_name }}Registry:
    """
    Registry for {{ class_name }} objects.
    """

    def __init__(self):
        self.items = {}

    def register(self, item):
        self.items[item.object_id] = item
        return item

    def get(self, object_id: str):
        return self.items.get(object_id)

    def all(self):
        return list(self.items.values())
