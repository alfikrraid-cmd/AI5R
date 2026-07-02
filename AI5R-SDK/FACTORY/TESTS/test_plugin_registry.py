"""
AI5R Plugin Registry Test
FM-004.3
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "AI5R-SDK" / "FACTORY"))

from plugin_registry import PluginRegistry


class DummyPlugin:

    name = "dummy"
    version = "1.0"

    def supports(self):
        return ["test", "dummy"]


registry = PluginRegistry()
registry.register(DummyPlugin())

assert registry.count() == 1
assert registry.names() == ["dummy"]
assert registry.get("dummy").name == "dummy"
assert len(registry.supports("test")) == 1

print("Plugin Registry Test OK")
