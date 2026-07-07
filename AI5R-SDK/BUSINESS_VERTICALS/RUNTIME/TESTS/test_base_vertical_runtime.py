from BUSINESS_VERTICALS.RUNTIME.vertical_runtime import BaseVerticalRuntime


class DemoRuntime(BaseVerticalRuntime):
    PRODUCT_NAME = "Demo OS"


def test_base_vertical_runtime():
    runtime = DemoRuntime(root_path=".")

    runtime.start()

    result = runtime.run_goal("Create business plan")

    assert result["status"] == "SUCCESS"
    assert result["product"] == "DEMO_OS"
    assert result["pipeline_id"].startswith("PIPE-CMD-")

    assert runtime.health() == "ACTIVE"
