from PRODUCT_FACTORY.KNOWLEDGE_BINDING import (
    KnowledgeBindingRegistry,
    KnowledgeBinding,
)



def test_knowledge_binding():


    registry = KnowledgeBindingRegistry()


    result = registry.bind(

        KnowledgeBinding(

            product_id="UMKM-AI-001",

            capability_id="CAP-MARKET",

            knowledge_domain="MARKETING"

        )

    )


    assert result["status"] == "BOUND"


    data = registry.find_by_product(
        "UMKM-AI-001"
    )


    assert data[0].knowledge_domain == "MARKETING"
