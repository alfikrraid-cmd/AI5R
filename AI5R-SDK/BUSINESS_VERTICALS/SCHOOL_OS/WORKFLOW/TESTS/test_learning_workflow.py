from BUSINESS_VERTICALS.SCHOOL_OS.WORKFLOW import (
    SchoolLearningWorkflowEngine,
    LearningWorkflow,
)



def test_learning_workflow():


    engine = SchoolLearningWorkflowEngine()


    result = engine.create(

        LearningWorkflow(

            workflow_id="LESSON-001",

            name="Lesson Planning Workflow",

            steps=[

                "ANALYZE_OBJECTIVE",

                "CREATE_LESSON_PLAN",

                "CREATE_ASSESSMENT"

            ]

        )

    )


    assert result["status"] == "CREATED"


    execution = engine.execute(
        "LESSON-001"
    )


    assert execution["status"] == "EXECUTED"


    assert execution["steps"] == 3
