from MANUFACTURING import ProductionLine


def test_line_is_valid():
    line = ProductionLine(
        line_id="LINE-001",
        line_name="Website Production",
        product_type="WEBSITE",
        station_ids=(
            "INTENT",
            "RESEARCH",
            "ARCH",
            "QA",
            "DEPLOY",
        ),
    )

    assert line.validate()
    assert line.station_count() == 5


def test_line_requires_station():
    line = ProductionLine(
        line_id="LINE-002",
        line_name="Empty",
        product_type="ERP",
        station_ids=(),
    )

    assert line.validate() is False
