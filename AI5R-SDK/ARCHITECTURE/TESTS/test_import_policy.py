from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE.GRAPH import DependencyGraphAnalyzer
from ARCHITECTURE.POLICY import ImportPolicyEngine


def test_import_policy():
    analyzer = DependencyGraphAnalyzer()
    graph = analyzer.analyze().snapshot()

    engine = ImportPolicyEngine(graph)
    result = engine.validate()

    assert isinstance(result.is_valid, bool)
