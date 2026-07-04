import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from BRAIN.enterprise_cognitive_station import EnterpriseCognitiveStation


class DummyStation(EnterpriseCognitiveStation):

    input_object_type = "dummy"

    output_object_type = "dummy"

    def transform(self, enterprise_object):
        return {
            "processed": True,
            "input": enterprise_object,
        }


def test_station_process():

    station = DummyStation()

    result = station.process({"hello": "world"})

    assert result["processed"] is True

    assert result["input"]["hello"] == "world"


def test_station_validate():

    station = DummyStation()

    try:
        station.process(None)
        assert False
    except ValueError:
        assert True
