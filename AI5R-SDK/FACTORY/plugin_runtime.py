"""
AI5R Plugin Runtime
FM-004.4
"""

from plugin_loader import PluginLoader
from plugin_registry import PluginRegistry


class PluginRuntime:

    def __init__(self):
        self.loader = PluginLoader()
        self.registry = PluginRegistry()

    def load(self, plugin_path):
        self.loader.discover(plugin_path)

        for plugin in self.loader.plugins.values():
            self.registry.register(plugin)

    def plugins(self):
        return self.registry.names()

    def plugin(self, name):
        return self.registry.get(name)

    def doctor(self):
        report = {}

        for name in self.registry.names():
            plugin = self.registry.get(name)
            report[name] = plugin.self_test()

        return report
