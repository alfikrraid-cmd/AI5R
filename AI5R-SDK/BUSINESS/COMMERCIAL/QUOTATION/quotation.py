from dataclasses import dataclass, field
from datetime import datetime, UTC

from BUSINESS.COMMERCIAL.QUOTATION.quotation_item import QuotationItem


@dataclass
class Quotation:
    quotation_id: str
    customer_id: str
    currency: str = "IDR"
    tax_rate: float = 0
    items: list[QuotationItem] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def subtotal(self):
        return sum(item.total for item in self.items)

    @property
    def tax(self):
        return self.subtotal * self.tax_rate

    @property
    def grand_total(self):
        return self.subtotal + self.tax
