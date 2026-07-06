from COMMAND_CENTER.API import AI5RCommandAPI


def test_command_api_health():

    api = AI5RCommandAPI()

    result = api.health()

    assert result.status == "ONLINE"



def test_send_command():

    api = AI5RCommandAPI()

    result = api.send_command(
        {
            "command": "create_report"
        }
    )

    assert result.status == "ACCEPTED"
    assert result.data["queue_size"] == 1
