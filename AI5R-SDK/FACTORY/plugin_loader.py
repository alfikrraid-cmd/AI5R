"""
AI5R Plugin Loader
FM-004.4
"""

from pathlib import Path
import importlib.util
import sys


class PluginLoader:

    def __init__(self):
        self.plugins = {}

    def discover(self, root):

        root = Path(root)

        if not root.exists():
            return

        factory_root = root.parent
        if str(factory_root) not in sys.path:
            sys.path.insert(0, str(factory_root))

        self.plugins = {}

        for file in root.rglob("*.py"):

            if file.name.startswith("__"):
                continue

            if file.name == "plugin.py":
                continue

            spec = importlib.util.spec_from_file_location(
                file.stem,
                file
            )

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            if hasattr(module, "Plugin"):
                plugin = module.Plugin()
                self.plugins[plugin.name] = plugin

    def names(self):
        return sorted(self.plugins.keys())

    def get(self, name):
        return self.plugins.get(name)
