from COMMAND_CENTER.API.command_api import AI5RCommandAPI



def test_events_api():

    api = AI5RCommandAPI()


    api.register_event(
        "BOOT",
        {
            "service":"AI5R_KERNEL"
        }
    )


    response = api.events()


    assert response.status == "OK"

    assert len(
        response.data["events"]
    ) == 1


    assert (
        response.data["events"][0]["event_type"]
        == "BOOT"
    )
