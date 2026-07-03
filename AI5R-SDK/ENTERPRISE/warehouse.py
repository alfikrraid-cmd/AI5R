"""
AI5R Warehouse Framework
EL-005

Generic digital warehouse for AI5R Enterprise assets.
A Warehouse stores, loads, searches, versions, publishes, and archives
Enterprise Objects without exposing storage infrastructure details.
"""

from typing import Dict, List, Optional

from ENTERPRISE.enterprise_object import EnterpriseObject


class Warehouse:
    def __init__(self, warehouse_type: str):
        self.warehouse_type = warehouse_type
        self.items: Dict[str, EnterpriseObject] = {}

    def store(self, item: EnterpriseObject) -> EnterpriseObject:
        if item.type != self.warehouse_type:
            raise ValueError(
                f"Invalid warehouse item type: expected {self.warehouse_type}, got {item.type}"
            )

        if item.code in self.items:
            raise ValueError(f"Item already exists in warehouse: {item.code}")

        self.items[item.code] = item
        return item

    def load(self, code: str) -> Optional[EnterpriseObject]:
        return self.items.get(code)

    def list(self) -> List[EnterpriseObject]:
        return list(self.items.values())

    def search_by_tag(self, tag: str) -> List[EnterpriseObject]:
        return [item for item in self.items.values() if tag in item.tags]

    def version(self, code: str, version: str) -> EnterpriseObject:
        item = self.load(code)

        if item is None:
            raise KeyError(f"Item not found in warehouse: {code}")

        item.version = version
        item.touch()
        return item

    def publish(self, code: str) -> EnterpriseObject:
        item = self.load(code)

        if item is None:
            raise KeyError(f"Item not found in warehouse: {code}")

        item.update_status("published")
        return item

    def archive(self, code: str) -> EnterpriseObject:
        item = self.load(code)

        if item is None:
            raise KeyError(f"Item not found in warehouse: {code}")

        item.update_status("archived")
        return item

    def to_dict(self) -> Dict:
        return {
            "warehouse_type": self.warehouse_type,
            "count": len(self.items),
            "items": [item.to_dict() for item in self.items.values()],
        }
