from BUSINESS_VERTICALS.AUDITOR_OS.RUNTIME_INTEGRATION import (
    AuditorOSRuntimeEngine,
)



def test_auditor_os_runtime():


    runtime = AuditorOSRuntimeEngine().start()


    assert runtime.name == "AI5R AUDITOR OS"


    assert runtime.status == "ACTIVE"


    assert len(
        runtime.modules
    ) == 6


    assert runtime.agents == 3
