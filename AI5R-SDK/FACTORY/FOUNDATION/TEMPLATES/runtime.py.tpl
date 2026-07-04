class {{ class_name }}Runtime:
    """
    Runtime executor for {{ class_name }}.
    """

    def run(self, item):
        return {
            "status": "executed",
            "object_id": item.object_id,
            "name": item.name,
        }
