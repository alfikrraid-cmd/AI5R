"""
AI5R Dummy Plugin
FM-004.4
"""

from PLUGINS.plugin import FactoryPlugin


class Plugin(FactoryPlugin):

    name = "dummy"
    version = "1.0"
    author = "AI5R"

    def supports(self):
        return ["dummy"]

    def generate(self, manifest, output):
        print("Dummy Plugin")

    def self_test(self):
        return True
