"""
AI5R PostgreSQL Plugin
FM-004.3
"""

from AI5R_SDK.FACTORY.PLUGINS.plugin import FactoryPlugin


class PostgreSQLPlugin(FactoryPlugin):

    name = "postgres"
    version = "1.0"

    def supports(self):
        return [
            "sql",
            "postgres"
        ]

    def generate(self, manifest, output):
        """
        Placeholder.

        FM-004.4 akan memindahkan SQL Generator
        ke sini tanpa mengubah behaviour.
        """
        print("PostgreSQL Plugin")
