import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import (
    EnterpriseBrainConnector,
    ServiceBus,
    ServiceContainer,
)

from DIGITAL_ORGANIZATION import (
    CompanyRuntime,
    OrganizationRuntime,
)


def test_connect_company_runtime():
    container = ServiceContainer()
    bus = ServiceBus()

    connector = EnterpriseBrainConnector(
        container=container,
        service_bus=bus,
    )

    runtime = CompanyRuntime(
        OrganizationRuntime("AI5R")
    )

    result = connector.connect(runtime)

    assert result["status"] == "CONNECTED"
    assert connector.runtime() is runtime


def test_connection_publishes_event():
    container = ServiceContainer()
    bus = ServiceBus()

    connector = EnterpriseBrainConnector(
        container=container,
        service_bus=bus,
    )

    runtime = CompanyRuntime(
        OrganizationRuntime("AI5R")
    )

    connector.connect(runtime)

    history = bus.history()

    assert len(history) == 1
    assert history[0].event_type == "COMPANY_CONNECTED"
    assert history[0].payload["organization"] == "AI5R"
