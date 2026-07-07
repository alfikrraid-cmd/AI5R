from BUSINESS_VERTICALS.UMKM_OS.WORKFLOW import (
    UMKMWorkflowEngine,
    UMKMWorkflow,
    WorkflowStep,
)



def test_umkm_workflow():


    engine = UMKMWorkflowEngine()


    result = engine.create(

        UMKMWorkflow(

            workflow_id="UMKM-SALES-FLOW-001",

            name="Customer Acquisition Flow",

            steps=[

                WorkflowStep(

                    step_id="1",

                    agent_id="MARKETING-001",

                    action="CREATE_CAMPAIGN"

                ),

                WorkflowStep(

                    step_id="2",

                    agent_id="SALES-001",

                    action="FOLLOW_UP_CUSTOMER"

                )

            ]

        )

    )


    assert result["status"] == "CREATED"


    execution = engine.execute(
        "UMKM-SALES-FLOW-001"
    )


    assert execution["status"] == "EXECUTED"
    assert execution["steps"] == 2
