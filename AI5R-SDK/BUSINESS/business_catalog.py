class BusinessCatalog:

    def __init__(self):
        self._items = {}

    def register(self, item):

        item_id = (
            getattr(item, "business_model_id", None)
            or getattr(item, "pricing_id", None)
            or getattr(item, "segment_id", None)
            or getattr(item, "delivery_id", None)
        )

        if not item_id:
            raise ValueError("Business catalog item requires an id")

        self._items[item_id] = item

        return {
            "status": "REGISTERED",
            "item_id": item_id,
            "object_type": item.object_type,
        }

    def get(self, item_id):
        return self._items.get(item_id)

    def list_all(self):
        return list(self._items.values())

    def list_by_type(self, object_type):
        return [
            item
            for item in self._items.values()
            if item.object_type == object_type
        ]

    def list_by_product(self, product_code):
        return [
            item
            for item in self._items.values()
            if getattr(item, "product_code", None) == product_code
        ]
