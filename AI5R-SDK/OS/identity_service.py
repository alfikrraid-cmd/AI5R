from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Identity:
    identity_id: str
    identity_type: str
    name: str
    attributes: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class IdentityService:
    def __init__(self):
        self._registry: dict[str, Identity] = {}

    def register(
        self,
        identity_id: str,
        identity_type: str,
        name: str,
        attributes: dict[str, Any] | None = None,
    ) -> Identity:
        if identity_id in self._registry:
            raise ValueError("identity already exists")

        identity = Identity(
            identity_id=identity_id,
            identity_type=identity_type,
            name=name,
            attributes=attributes or {},
        )

        self._registry[identity_id] = identity
        return identity

    def get(self, identity_id: str) -> Identity | None:
        return self._registry.get(identity_id)

    def update(
        self,
        identity_id: str,
        attributes: dict[str, Any],
    ) -> Identity:
        identity = self.get(identity_id)

        if identity is None:
            raise ValueError("identity not found")

        identity.attributes.update(attributes)
        return identity

    def unregister(self, identity_id: str) -> bool:
        if identity_id not in self._registry:
            return False

        del self._registry[identity_id]
        return True

    def list(self) -> list[Identity]:
        return list(self._registry.values())
