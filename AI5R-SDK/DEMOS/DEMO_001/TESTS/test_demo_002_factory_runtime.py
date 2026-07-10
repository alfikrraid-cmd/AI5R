from pathlib import Path

from DEMOS.DEMO_001.login_api_demo import run_demo


def test_demo_generates_downloadable_zip():

    result = run_demo()

    factory = result["factory"]

    assert factory["status"] == "FACTORY_COMPLETED"

    assert factory["validation"]["status"] == "BUILD_VALID"

    assert Path(
        factory["archive"]["zip_path"]
    ).exists()

    assert factory["archive"]["zip_path"].endswith(".zip")
