from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from RUNTIME.PERFORMANCE import PerformanceProfiler, LazyLoader


def test_profiler():
    profiler = PerformanceProfiler()

    def job():
        return sum(range(1000))

    result = profiler.profile("test_module", job)

    assert result is not None
    assert len(profiler.records) == 1


def test_lazy_loader():
    loader = LazyLoader()

    json_mod = loader.load("json")

    assert json_mod is not None
