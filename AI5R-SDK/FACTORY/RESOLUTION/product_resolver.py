from FACTORY.ORDERS.manufacturing_order import ManufacturingOrder


class ProductResolver:

    PRODUCT_PACKS = {
        "WEBSITE": "WEBSITE_PRODUCT_PACK",
        "AUDIT_OFFICE": "AUDIT_OFFICE_PRODUCT_PACK",
        "ACCOUNTING_OFFICE": "ACCOUNTING_OFFICE_PRODUCT_PACK",
    }

    def resolve(self, order: ManufacturingOrder) -> str:
        if order.status != "VALIDATED":
            raise ValueError(
                "Manufacturing Order must be VALIDATED before resolution."
            )

        try:
            return self.PRODUCT_PACKS[order.requested_product]
        except KeyError:
            raise ValueError(
                f"Unknown product: {order.requested_product}"
            )
