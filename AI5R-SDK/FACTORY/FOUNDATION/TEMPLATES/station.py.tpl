class {{ class_name }}ManufacturingStation:
    """
    Manufacturing Station for {{ class_name }}.
    """

    def manufacture(self, payload: dict):
        return {
            "station": "{{ class_name }}ManufacturingStation",
            "status": "manufactured",
            "payload": payload,
        }
