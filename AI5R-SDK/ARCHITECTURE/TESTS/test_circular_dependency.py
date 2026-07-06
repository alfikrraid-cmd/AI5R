from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.GRAPH import DependencyGraphAnalyzer
from ARCHITECTURE.CYCLE import CircularDependencyDetector


def test_no_circular_dependency():
    analyzer = DependencyGraphAnalyzer()
    graph = analyzer.analyze().snapshot()

    detector = CircularDependencyDetector(graph)
    result = detector.detect()

    assert result.has_cycle is False
    assert result.cycles == []
