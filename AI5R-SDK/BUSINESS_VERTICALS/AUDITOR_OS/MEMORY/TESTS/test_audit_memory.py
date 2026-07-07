from BUSINESS_VERTICALS.AUDITOR_OS.MEMORY import (
    AuditMemorySystem,
    AuditMemory,
)



def test_audit_memory():


    memory = AuditMemorySystem()


    result = memory.store(

        AuditMemory(

            audit_id="AUDIT-001",

            category="TAX",

            experience={

                "issue":
                "missing_tax_document",

                "impact":
                "compliance_risk"

            }

        )

    )


    assert result["status"] == "STORED"


    saved = memory.recall(
        "AUDIT-001"
    )


    assert saved.category == "TAX"


    pattern = memory.analyze_pattern(
        "AUDIT-001"
    )


    assert (
        pattern["pattern"]
        ==
        "RECURRING_COMPLIANCE_ISSUE"
    )
