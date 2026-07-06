from REALTIME_ENGINE.GOVERNANCE_GUARD import (
    RealtimeGovernanceGuard,
)


def test_governance_allow():


    guard = RealtimeGovernanceGuard()


    result = guard.check(
        {
            "action": "create marketing plan"
        }
    )


    assert result["status"] == "ALLOWED"



def test_governance_block():


    guard = RealtimeGovernanceGuard()


    result = guard.check(
        {
            "action": "create illegal method"
        }
    )


    assert result["status"] == "BLOCKED"
