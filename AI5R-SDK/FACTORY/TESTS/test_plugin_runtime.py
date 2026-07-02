"""
AI5R Plugin Runtime Test
FM-004.4
"""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
FACTORY = ROOT / "AI5R-SDK" / "FACTORY"
PLUGINS = FACTORY / "PLUGINS"

sys.path.insert(0, str(FACTORY))

from plugin_runtime import PluginRuntime

runtime = PluginRuntime()
runtime.load(PLUGINS)

assert runtime.plugins() == ["dummy"]
assert runtime.doctor() == {"dummy": True}

print("FM-004.4 Plugin Runtime OK")
