from BUSINESS_VERTICALS.SCHOOL_OS.KNOWLEDGE import (
    SchoolKnowledgeRegistry,
    EducationKnowledge,
)



def test_school_knowledge():


    registry = SchoolKnowledgeRegistry()


    result = registry.register(

        EducationKnowledge(

            knowledge_id="EDU-CURRICULUM",

            domain="CURRICULUM",

            topics=[

                "learning_objective",

                "lesson_structure",

                "assessment"

            ]

        )

    )


    assert result["status"] == "REGISTERED"


    knowledge = registry.get(
        "EDU-CURRICULUM"
    )


    assert "assessment" in knowledge.topics
