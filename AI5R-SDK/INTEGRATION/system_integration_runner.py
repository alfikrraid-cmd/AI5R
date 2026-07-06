from __future__ import annotations

from .system_integration_report import IntegrationReport


class SystemIntegrationRunner:
    def __init__(self):
        self.report = IntegrationReport()

    def run_step(self, name: str, fn):
        try:
            fn()
            self.report.add_step(name)
        except Exception:
            self.report.add_failure(name)
            raise

    def run(self, steps):
        for name, fn in steps:
            self.run_step(name, fn)

        return self.report
