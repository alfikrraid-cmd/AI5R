from BUSINESS.pricing_model import PricingModel


class PricingEngine:

    def calculate(
        self,
        pricing: PricingModel,
        used_units: int = 0,
    ):

        overage_units = max(
            0,
            used_units - pricing.included_units,
        )

        total_amount = pricing.price_amount + (
            overage_units * pricing.overage_rate
        )

        return {
            "status": "CALCULATED",
            "pricing": pricing,
            "used_units": used_units,
            "included_units": pricing.included_units,
            "overage_units": overage_units,
            "total_amount": total_amount,
            "currency": pricing.currency,
        }
