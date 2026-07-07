from OSA.INTELLIGENCE.CONVERSATION import (
    OSAConversationEngine,
)



def test_conversation_engine():


    engine = OSAConversationEngine()


    result = engine.analyze(

        "Build AI marketplace system"

    )


    assert (
        "marketplace"
        in result.understanding
    )


    assert (
        "opportunity"
        in result.recommendation
        or
        "AI"
        in result.recommendation
    )
