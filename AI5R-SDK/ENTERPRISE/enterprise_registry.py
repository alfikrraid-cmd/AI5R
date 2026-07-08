from .enterprise import EnterpriseObject
from .enterprise_identity import EnterpriseIdentityGenerator


class EnterpriseRegistry:

    def __init__(
        self,
        identity_generator=None,
    ):
        self.identity_generator = (
            identity_generator
            or EnterpriseIdentityGenerator()
        )

        self.objects = {}

    def register(
        self,
        object_type: str,
        name: str,
        metadata=None,
    ):

        object_id = self.identity_generator.generate(
            object_type
        )

        obj = EnterpriseObject(
            object_id=object_id,
            object_type=object_type,
            name=name,
            metadata=metadata or {},
        )

        self.objects[object_id] = obj

        return obj

    def get(
        self,
        object_id: str,
    ):
        return self.objects.get(
            object_id
        )

    def list_by_type(
        self,
        object_type: str,
    ):
        return [
            obj
            for obj in self.objects.values()
            if obj.object_type == object_type
        ]

    def list_all(self):
        return list(
            self.objects.values()
        )
