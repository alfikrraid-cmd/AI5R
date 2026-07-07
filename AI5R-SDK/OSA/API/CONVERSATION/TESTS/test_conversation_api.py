from OSA.API.CONVERSATION import (
    OSAConversationAPI,
)



def test_conversation_api():


    api = OSAConversationAPI()


    result = api.process(

        "Create AI school system"

    )


    assert (
        "AI school"
        in result.message
    )


    assert (
        "blueprint"
        in result.recommendation
    )
