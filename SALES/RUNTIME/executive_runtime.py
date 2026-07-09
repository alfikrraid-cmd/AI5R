from BUSINESS.COMMERCIAL.CONTRACT import ContractEngine
from BUSINESS.COMMERCIAL.QUOTATION import QuotationEngine, QuotationItem
from SALES.CONTRACTS.executive_goal import ExecutiveGoal
from SALES.CONTRACTS.sales_workforce_contract import SalesTarget
from SALES.CRM import Customer, CustomerInteraction, SalesCRMRuntime
from SALES.PIPELINE import PROPOSAL, SalesOpportunity, SalesPipeline
from SALES.PROPOSAL import ProposalGenerator
from SALES.REPORTING.executive_report import ExecutiveReport
from SALES.RUNTIME.sales_executive_runtime import SalesExecutiveRuntime


class SalesExecutiveOrchestrator:
    executive_name = "Sales Executive"

    def __init__(self):
        self.goal: ExecutiveGoal | None = None
        self.planner = SalesExecutiveRuntime()
        self.crm = SalesCRMRuntime()
        self.pipeline = SalesPipeline()
        self.proposal_generator = ProposalGenerator()
        self.quotation_engine = QuotationEngine()
        self.contract_engine = ContractEngine()

        self.sales_plan = None
        self.proposal = None
        self.quotation = None
        self.contract = None

    def receive_goal(self, goal: ExecutiveGoal):
        if goal.target_value <= 0:
            raise ValueError("Goal target value must be greater than zero")

        self.goal = goal
        return goal

    def analyze(self):
        if self.goal is None:
            raise ValueError("Goal is required")

        return {
            "goal_id": self.goal.goal_id,
            "target_value": self.goal.target_value,
            "period": self.goal.period,
        }

    def create_plan(
        self,
        average_deal_size: float,
        conversion_rate: float,
    ):
        if self.goal is None:
            raise ValueError("Goal is required")

        self.sales_plan = self.planner.create_sales_plan(
            target=SalesTarget(
                revenue_target=self.goal.target_value,
                period=self.goal.period,
                currency=self.goal.currency,
            ),
            average_deal_size=average_deal_size,
            conversion_rate=conversion_rate,
        )

        return self.sales_plan

    def execute(
        self,
        customer_id: str,
        customer_name: str,
        opportunity_id: str,
        opportunity_value: float,
    ):
        if self.goal is None:
            raise ValueError("Goal is required")

        customer = Customer(
            customer_id=customer_id,
            name=customer_name,
            segment="ENTERPRISE",
            status="QUALIFIED",
        )
        self.crm.add_customer(customer)

        self.crm.record_interaction(
            CustomerInteraction(
                interaction_id=f"INT-{customer_id}",
                customer_id=customer_id,
                interaction_type="EXECUTIVE_ORCHESTRATION",
                notes="Sales Executive created customer memory during execution.",
            )
        )

        opportunity = SalesOpportunity(
            opportunity_id=opportunity_id,
            customer=customer_name,
            value=opportunity_value,
        )
        self.pipeline.add(opportunity)
        self.pipeline.move(opportunity_id, PROPOSAL)

        self.proposal = self.proposal_generator.generate(
            proposal_id=f"PROP-{opportunity_id}",
            customer_id=customer_id,
            opportunity_id=opportunity_id,
            title=f"{customer_name} Sales Proposal",
            problem_statement="Customer needs structured commercial execution.",
            proposed_solution="Provide AI5R-powered sales workflow with proposal, quotation, and contract.",
            scope=[
                "Sales planning",
                "Pipeline management",
                "CRM memory",
                "Proposal generation",
                "Quotation generation",
                "Contract generation",
            ],
            timeline="14 days",
            investment=opportunity_value,
            currency=self.goal.currency,
        )

        self.quotation = self.quotation_engine.create(
            quotation_id=f"Q-{opportunity_id}",
            customer_id=customer_id,
            currency=self.goal.currency,
            tax_rate=0.11,
        )

        self.quotation_engine.add_item(
            self.quotation,
            QuotationItem(
                description=self.proposal.title,
                quantity=1,
                unit_price=opportunity_value,
            ),
        )

        self.contract = self.contract_engine.create(
            contract_id=f"CON-{opportunity_id}",
            customer_id=customer_id,
            title=f"{customer_name} Commercial Contract",
            value=self.quotation.grand_total,
            currency=self.goal.currency,
        )

        return {
            "customer": customer,
            "opportunity": opportunity,
            "proposal": self.proposal,
            "quotation": self.quotation,
            "contract": self.contract,
        }

    def monitor(self):
        return {
            "pipeline_open_value": self.pipeline.open_value(),
            "pipeline_forecast": self.pipeline.forecast_value(),
            "won_value": self.pipeline.won_value(),
            "lost_value": self.pipeline.lost_value(),
        }

    def report(self):
        if self.goal is None:
            raise ValueError("Goal is required")

        monitor = self.monitor()

        return ExecutiveReport(
            executive=self.executive_name,
            goal=self.goal.description,
            summary="Sales Executive is ready with plan, CRM, pipeline, proposal, quotation, and contract.",
            kpis={
                "target_value": self.goal.target_value,
                "required_leads": getattr(self.sales_plan, "required_leads", 0),
                "required_closings": getattr(self.sales_plan, "required_closings", 0),
                "pipeline_forecast": monitor["pipeline_forecast"],
                "pipeline_open_value": monitor["pipeline_open_value"],
            },
            recommendations=[
                "Increase qualified lead generation.",
                "Follow up proposal-ready opportunities.",
            ],
            next_actions=[
                "Review pipeline weekly.",
                "Convert proposal into active contract after approval.",
            ],
        )
