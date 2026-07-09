from dataclasses import dataclass


@dataclass
class QuotationItem:
    description: str
    quantity: float
    unit_price: float
    discount: float = 0

    @property
    def subtotal(self):
        return self.quantity * self.unit_price

    @property
    def total(self):
        return self.subtotal - self.discount
