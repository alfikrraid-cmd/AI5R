from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from OS.API_GATEWAY import APIGateway


def test_api_gateway_success():
    api = APIGateway()

    api.register("hello", lambda p: {"msg": "world"})

    res = api.call("hello", {})

    assert res.status == "200"
    assert res.data["msg"] == "world"


def test_api_gateway_404():
    api = APIGateway()

    res = api.call("missing", {})

    assert res.status == "404"
