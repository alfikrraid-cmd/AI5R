from PRODUCT_FACTORY.WORKFLOW_FACTORY import (
    WorkflowFactory,
    ProductWorkflow,
    WorkflowStep,
)



def test_workflow_creation():


    factory = WorkflowFactory()


    workflow = ProductWorkflow(

        workflow_id="WF-UMKM-SALES-001",

        product_id="UMKM-AI-001",

        steps=[

            WorkflowStep(

                step_id="1",

                agent_id="AGENT-MARKETING-001",

                action="ANALYZE_CUSTOMER"

            )

        ]

    )


    result = factory.create(
        workflow
    )


    assert result["status"] == "CREATED"


    saved = factory.get(
        "WF-UMKM-SALES-001"
    )


    assert saved.product_id == "UMKM-AI-001"
    assert saved.steps[0].action == "ANALYZE_CUSTOMER"
