from SALES.PIPELINE import (
    SalesOpportunity,
    SalesPipeline,
    PROPOSAL,
    WON,
)


def test_pipeline_forecast():
    pipeline = SalesPipeline()

    pipeline.add(
        SalesOpportunity(
            "OPP-001",
            "PT ABC",
            100_000_000,
        )
    )

    pipeline.move("OPP-001", PROPOSAL)

    assert pipeline.forecast_value() == 60_000_000


def test_pipeline_won():
    pipeline = SalesPipeline()

    pipeline.add(
        SalesOpportunity(
            "OPP-001",
            "PT ABC",
            100_000_000,
        )
    )

    pipeline.move("OPP-001", WON)

    assert pipeline.won_value() == 100_000_000
