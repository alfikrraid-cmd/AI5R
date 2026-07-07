from BUSINESS_VERTICALS.AUDITOR_OS.RUNTIME import (
    AuditorRuntime,
    AuditorVertical,
)



def test_auditor_runtime():


    runtime = AuditorRuntime()


    result = runtime.register(

        AuditorVertical(

            vertical_id="AUDITOR-OS",

            name="AI5R AUDITOR OS",

            domain="COMPLIANCE",

            agents=[

                "AUDITOR_AGENT",

                "RISK_AGENT",

                "COMPLIANCE_AGENT"

            ]

        )

    )


    assert result["status"] == "REGISTERED"


    auditor = runtime.get(
        "AUDITOR-OS"
    )


    assert auditor.domain == "COMPLIANCE"


    assert len(
        auditor.agents
    ) == 3
