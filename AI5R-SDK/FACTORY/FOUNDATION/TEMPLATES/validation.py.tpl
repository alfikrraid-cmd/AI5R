class {{ class_name }}Validator:
    """
    Validator for {{ class_name }}.
    """

    def validate(self, item) -> bool:
        return bool(item.object_id and item.name)
