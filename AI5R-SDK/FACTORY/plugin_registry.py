"""
AI5R Plugin Registry
FM-004.3
"""


class PluginRegistry:

    def __init__(self):
        self._plugins = {}

    def register(self, plugin):

        self._plugins[plugin.name] = plugin

    def names(self):

        return sorted(self._plugins.keys())

    def get(self, name):

        return self._plugins.get(name)

    def supports(self, capability):

        result = []

        for plugin in self._plugins.values():

            if capability in plugin.supports():
                result.append(plugin)

        return result

    def count(self):

        return len(self._plugins)
