from BUSINESS_VERTICALS.AUDITOR_OS.KNOWLEDGE import (
    AuditorKnowledgeRegistry,
    ComplianceKnowledge,
)



def test_auditor_knowledge():


    registry = AuditorKnowledgeRegistry()


    result = registry.register(

        ComplianceKnowledge(

            knowledge_id="COMPLIANCE-001",

            domain="ACCOUNTING",

            topics=[

                "financial_records",

                "transaction_review",

                "risk_management"

            ]

        )

    )


    assert result["status"] == "REGISTERED"


    knowledge = registry.get(
        "COMPLIANCE-001"
    )


    assert knowledge.domain == "ACCOUNTING"


    assert (
        "risk_management"
        in knowledge.topics
    )
