from copy import deepcopy
from datetime import datetime
from uuid import uuid4


class WarehouseAdapterStation:
    """
    LTSA-005 Warehouse Adapter Station

    Converts Reality Object into Warehouse Object.
    """

    def adapt(self, reality):
        if reality.get("object_type") != "reality":
            raise ValueError("Input must be a Reality Object")

        return {
            "id": str(uuid4()),
            "object_type": "warehouse",
            "entity_type": reality["source_type"],
            "payload": deepcopy(reality),
            "status": "adapted",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
