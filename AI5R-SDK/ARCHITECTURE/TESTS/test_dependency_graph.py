from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.GRAPH import DependencyGraphAnalyzer


def test_dependency_graph_scan():
    analyzer = DependencyGraphAnalyzer()

    graph = analyzer.analyze()

    assert graph is not None
    assert isinstance(graph.snapshot(), dict)
    assert len(graph.snapshot()) > 0
