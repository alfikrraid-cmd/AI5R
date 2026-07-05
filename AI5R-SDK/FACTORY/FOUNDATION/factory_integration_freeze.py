from pathlib import Path


class FactoryIntegrationFreeze:
    """
    Verifies Sprint 16 Factory Integration freeze artifacts.
    """

    REQUIRED_FILES = [
        "factory_orchestrator.py",
        "manufacturing_context.py",
        "manufacturing_station.py",
        "station_registry.py",
        "pipeline_builder.py",
        "manufacturing_event.py",
        "manufacturing_event_bus.py",
        "build_report.py",
        "build_workspace.py",
        "manufacturing_runtime.py",
        "DOCS/FI-010-SPRINT-16-FACTORY-INTEGRATION-FREEZE.md",
    ]

    def __init__(self, foundation_dir: str | Path):
        self.foundation_dir = Path(foundation_dir)

    def verify(self) -> dict:
        missing = []

        for relative_path in self.REQUIRED_FILES:
            path = self.foundation_dir / relative_path

            if not path.exists():
                missing.append(relative_path)

        if missing:
            return {
                "status": "NOT_FROZEN",
                "missing": missing,
            }

        return {
            "status": "FROZEN",
            "missing": [],
        }
