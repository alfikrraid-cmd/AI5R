"""
FM-005.5 Plugin Pipeline

Runs plugins against a CompilationUnit.
"""


class PluginPipeline:

    def __init__(self, plugins=None):
        self.plugins = plugins or []

    def add_plugin(self, plugin):
        self.plugins.append(plugin)

    def run(self, compilation_unit):
        results = []

        for plugin in self.plugins:
            result = plugin.run(compilation_unit)
            results.append(result)

        return results
