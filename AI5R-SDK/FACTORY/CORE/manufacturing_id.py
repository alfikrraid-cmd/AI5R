from uuid import uuid4


class ManufacturingID:
    @staticmethod
    def generate() -> str:
        return str(uuid4())
