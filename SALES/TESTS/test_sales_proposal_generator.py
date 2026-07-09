from SALES.PROPOSAL import ProposalGenerator, SalesProposal


def test_generate_sales_proposal():
    generator = ProposalGenerator()

    proposal = generator.generate(
        proposal_id="PROP-001",
        customer_id="CUST-001",
        opportunity_id="OPP-001",
        title="AI5R Sales Workforce Implementation",
        problem_statement="Customer needs a structured AI sales workforce.",
        proposed_solution="Implement Sales Executive AI with CRM, pipeline, and reporting.",
        scope=[
            "Sales pipeline setup",
            "CRM memory setup",
            "Proposal automation",
        ],
        timeline="14 days",
        investment=50_000_000,
    )

    assert isinstance(proposal, SalesProposal)
    assert proposal.proposal_id == "PROP-001"
    assert proposal.customer_id == "CUST-001"
    assert proposal.opportunity_id == "OPP-001"
    assert proposal.investment == 50_000_000
    assert "CRM memory setup" in proposal.scope


def test_reject_empty_proposal_id():
    generator = ProposalGenerator()

    try:
        generator.generate(
            proposal_id="",
            customer_id="CUST-001",
            opportunity_id="OPP-001",
            title="Test",
            problem_statement="Problem",
            proposed_solution="Solution",
            scope=[],
            timeline="7 days",
            investment=10_000_000,
        )
    except ValueError as exc:
        assert "Proposal ID" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_reject_negative_investment():
    generator = ProposalGenerator()

    try:
        generator.generate(
            proposal_id="PROP-001",
            customer_id="CUST-001",
            opportunity_id="OPP-001",
            title="Test",
            problem_statement="Problem",
            proposed_solution="Solution",
            scope=[],
            timeline="7 days",
            investment=-1,
        )
    except ValueError as exc:
        assert "Investment" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
