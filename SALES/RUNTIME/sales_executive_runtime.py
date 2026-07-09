from SALES.CONTRACTS.sales_workforce_contract import SalesPlan, SalesTarget


class SalesExecutiveRuntime:
    def create_sales_plan(
        self,
        target: SalesTarget,
        average_deal_size: float,
        conversion_rate: float,
    ) -> SalesPlan:
        if target.revenue_target <= 0:
            raise ValueError("Revenue target must be greater than zero")

        if average_deal_size <= 0:
            raise ValueError("Average deal size must be greater than zero")

        if conversion_rate <= 0 or conversion_rate > 1:
            raise ValueError("Conversion rate must be between 0 and 1")

        required_closings = int(-(-target.revenue_target // average_deal_size))
        required_leads = int(-(-required_closings // conversion_rate))

        return SalesPlan(
            target=target,
            required_leads=required_leads,
            required_closings=required_closings,
            conversion_rate=conversion_rate,
            actions=[
                "Define ideal customer profile",
                "Generate qualified leads",
                "Prioritize high-value opportunities",
                "Create weekly follow-up rhythm",
                "Review pipeline performance weekly",
            ],
            metadata={
                "average_deal_size": average_deal_size,
            },
        )
