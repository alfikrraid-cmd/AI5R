from BUSINESS_VERTICALS.AUDITOR_OS.WORKFLOW import (
    AuditWorkflowEngine,
    AuditWorkflow,
)



def test_audit_workflow():


    engine = AuditWorkflowEngine()


    result = engine.create(

        AuditWorkflow(

            workflow_id="AUDIT-001",

            name="Financial Audit Workflow",

            steps=[

                "RECEIVE_DOCUMENT",

                "REVIEW_DOCUMENT",

                "CHECK_COMPLIANCE",

                "ANALYZE_RISK",

                "GENERATE_REPORT"

            ]

        )

    )


    assert result["status"] == "CREATED"


    execution = engine.execute(
        "AUDIT-001"
    )


    assert execution["status"] == "EXECUTED"


    assert execution["steps"] == 5
