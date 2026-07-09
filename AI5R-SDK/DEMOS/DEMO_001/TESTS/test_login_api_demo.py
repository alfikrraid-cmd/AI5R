from DEMOS.DEMO_001.login_api_demo import run_demo


def test_demo_001_creates_canonical_manufacturing_order():
    result = run_demo()

    assert result["status"] == "DEMO_002_COMPLETED"
    assert result["order"].product_type == "FASTAPI_SERVICE"
    assert result["order"].validate() is True
    assert result["order"].metadata["source"] == "WORKFORCE"
