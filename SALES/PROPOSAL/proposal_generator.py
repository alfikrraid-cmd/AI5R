from SALES.PROPOSAL.proposal import SalesProposal


class ProposalGenerator:
    def generate(
        self,
        proposal_id: str,
        customer_id: str,
        opportunity_id: str,
        title: str,
        problem_statement: str,
        proposed_solution: str,
        scope: list[str],
        timeline: str,
        investment: float,
        currency: str = "IDR",
    ) -> SalesProposal:
        if not proposal_id:
            raise ValueError("Proposal ID is required")

        if not customer_id:
            raise ValueError("Customer ID is required")

        if not opportunity_id:
            raise ValueError("Opportunity ID is required")

        if investment < 0:
            raise ValueError("Investment cannot be negative")

        return SalesProposal(
            proposal_id=proposal_id,
            customer_id=customer_id,
            opportunity_id=opportunity_id,
            title=title,
            problem_statement=problem_statement,
            proposed_solution=proposed_solution,
            scope=scope,
            timeline=timeline,
            investment=investment,
            currency=currency,
        )
