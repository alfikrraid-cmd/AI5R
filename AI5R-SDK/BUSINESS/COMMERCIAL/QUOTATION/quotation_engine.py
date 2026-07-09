from BUSINESS.COMMERCIAL.QUOTATION.quotation import Quotation
from BUSINESS.COMMERCIAL.QUOTATION.quotation_item import QuotationItem


class QuotationEngine:
    def create(
        self,
        quotation_id: str,
        customer_id: str,
        currency: str = "IDR",
        tax_rate: float = 0.11,
    ) -> Quotation:
        if not quotation_id:
            raise ValueError("Quotation ID is required")

        if not customer_id:
            raise ValueError("Customer ID is required")

        if tax_rate < 0:
            raise ValueError("Tax rate cannot be negative")

        return Quotation(
            quotation_id=quotation_id,
            customer_id=customer_id,
            currency=currency,
            tax_rate=tax_rate,
        )

    def add_item(
        self,
        quotation: Quotation,
        item: QuotationItem,
    ) -> Quotation:
        if item.quantity < 0:
            raise ValueError("Quantity cannot be negative")

        if item.unit_price < 0:
            raise ValueError("Unit price cannot be negative")

        if item.discount < 0:
            raise ValueError("Discount cannot be negative")

        quotation.items.append(item)
        return quotation

    def remove_item(
        self,
        quotation: Quotation,
        index: int,
    ) -> Quotation:
        quotation.items.pop(index)
        return quotation
