from REALTIME_ENGINE.EVENT_BUS import (
    EventBus,
    EventMessage,
)


def test_event_publish_subscribe():

    bus = EventBus()

    received = []

    def handler(event):
        received.append(event.payload)


    bus.subscribe(
        "ORDER_CREATED",
        handler
    )


    event = EventMessage(
        event_type="ORDER_CREATED",
        payload={
            "order_id": "001"
        }
    )


    bus.publish(event)


    assert received[0]["order_id"] == "001"
