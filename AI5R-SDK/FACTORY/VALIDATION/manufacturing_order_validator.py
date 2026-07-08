from FACTORY.ORDERS.manufacturing_order import ManufacturingOrder


class ManufacturingOrderValidator:

    def validate(self, order: ManufacturingOrder) -> ManufacturingOrder:
        order.validate()
        order.status = "VALIDATED"
        return order
