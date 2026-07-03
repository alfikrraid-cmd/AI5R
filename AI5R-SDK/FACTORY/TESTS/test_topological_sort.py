import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from MANUFACTURING.topological_sort import TopologicalSorter


def test_sort():

    graph = {
        "sql": [],
        "schema": ["sql"],
        "openapi": ["schema"],
        "workflow": ["schema", "openapi"],
        "release": ["workflow"]
    }

    order = TopologicalSorter().sort(graph)

    assert order == [
        "sql",
        "schema",
        "openapi",
        "workflow",
        "release"
    ]

    print("FM-104.5 Topological Sort Test OK")


if __name__ == "__main__":
    test_sort()
