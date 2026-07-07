from BUSINESS_VERTICALS.UMKM_OS.KNOWLEDGE import (
    UMKMKnowledgeRegistry,
    KnowledgeDomain,
)



def test_umkm_knowledge():


    registry = UMKMKnowledgeRegistry()


    result = registry.register(

        KnowledgeDomain(

            domain_id="UMKM-MARKETING",

            name="Marketing Knowledge",

            topics=[

                "branding",

                "customer",

                "promotion"

            ]

        )

    )


    assert result["status"] == "REGISTERED"


    knowledge = registry.get(
        "UMKM-MARKETING"
    )


    assert "branding" in knowledge.topics
