from COMMAND_CENTER.CONTRACTS import (
    DashboardContract,
)


def test_dashboard_snapshot():

    contract = DashboardContract()

    result = contract.generate(
        {
            "system_status": "ONLINE",
            "active_agents": 5,
            "decisions": 12,
            "memories": 30,
            "governance": "ACTIVE"
        }
    )

    assert result.system_status == "ONLINE"
    assert result.active_agents == 5
    assert result.memories == 30
