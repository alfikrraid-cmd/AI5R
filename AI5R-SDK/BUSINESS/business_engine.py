from BUSINESS.business_model_object import BusinessModelObject


class BusinessEngine:

    def build(
        self,
        business_model: BusinessModelObject,
    ):

        return {
            "status": "READY",
            "business_model": business_model,
            "profile": {
                "product_code": business_model.product_code,
                "product_name": business_model.product_name,
                "target_customer": business_model.target_customer,
                "revenue_model": business_model.revenue_model,
                "delivery_model": business_model.delivery_model,
                "support_model": business_model.support_model,
                "pricing_strategy": business_model.pricing_strategy,
            },
        }
