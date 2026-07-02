"""
AI5R Factory Plugin Contract
FM-004.4
"""


class FactoryPlugin:

    name = "plugin"
    version = "1.0"
    author = "AI5R"

    def supports(self):
        return []

    def validate(self, manifest):
        return True

    def generate(self, manifest, output):
        raise NotImplementedError

    def self_test(self):
        return True
