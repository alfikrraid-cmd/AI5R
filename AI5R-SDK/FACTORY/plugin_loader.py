"""
AI5R Plugin Loader
FM-004.1
"""

from pathlib import Path
import importlib.util


class PluginLoader:

    def __init__(self):
        self.plugins = {}

    def discover(self, root):

        root = Path(root)

        if not root.exists():
            return

        for file in root.rglob("*.py"):

            if file.name.startswith("__"):
                continue

            name = file.stem

            spec = importlib.util.spec_from_file_location(
                name,
                file
            )

            module = importlib.util.module_from_spec(spec)

            spec.loader.exec_module(module)

            self.plugins[name] = module

    def names(self):
        return sorted(self.plugins.keys())

    def get(self, name):
        return self.plugins.get(name)
