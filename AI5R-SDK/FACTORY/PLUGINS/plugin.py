"""
AI5R Factory Plugin Contract
FM-004.2
"""


class FactoryPlugin:

    name = "plugin"
    version = "1.0"

    def supports(self):
        """
        Return plugin capability.
        """
        return []

    def generate(self, manifest, output):
        """
        Execute generation.
        """
        raise NotImplementedError
