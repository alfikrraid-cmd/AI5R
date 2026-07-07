from BUSINESS_VERTICALS.SCHOOL_OS.RUNTIME_INTEGRATION import (
    SchoolOSRuntimeEngine,
)



def test_school_os_runtime():


    runtime = SchoolOSRuntimeEngine().start()


    assert runtime.name == "AI5R SCHOOL OS"


    assert runtime.status == "ACTIVE"


    assert len(
        runtime.modules
    ) == 6


    assert runtime.agents == 4
