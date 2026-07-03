"""
AI5R Enterprise Registry Engine
EL-003

Generic in-memory registry engine for AI5R Enterprise Objects.
All enterprise registries should be built on top of this engine.
"""

from typing import Dict, List, Optional

from ENTERPRISE.enterprise_object import EnterpriseObject


class EnterpriseRegistry:
    def __init__(self, object_type: str):
        self.object_type = object_type
        self.objects: Dict[str, EnterpriseObject] = {}

    def register(self, obj: EnterpriseObject) -> EnterpriseObject:
        if obj.type != self.object_type:
            raise ValueError(
                f"Invalid object type: expected {self.object_type}, got {obj.type}"
            )

        if obj.code in self.objects:
            raise ValueError(f"Object already registered: {obj.code}")

        self.objects[obj.code] = obj
        return obj

    def get(self, code: str) -> Optional[EnterpriseObject]:
        return self.objects.get(code)

    def list(self) -> List[EnterpriseObject]:
        return list(self.objects.values())

    def update_status(self, code: str, status: str) -> EnterpriseObject:
        obj = self.get(code)

        if obj is None:
            raise KeyError(f"Object not found: {code}")

        obj.update_status(status)
        return obj

    def find_by_tag(self, tag: str) -> List[EnterpriseObject]:
        return [obj for obj in self.objects.values() if tag in obj.tags]

    def delete(self, code: str) -> None:
        if code not in self.objects:
            raise KeyError(f"Object not found: {code}")

        del self.objects[code]

    def to_dict(self) -> Dict:
        return {
            "object_type": self.object_type,
            "count": len(self.objects),
            "objects": [obj.to_dict() for obj in self.objects.values()],
        }
