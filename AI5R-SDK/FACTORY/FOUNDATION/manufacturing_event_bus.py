try:
    from .manufacturing_event import ManufacturingEvent
except ImportError:
    from manufacturing_event import ManufacturingEvent


class ManufacturingEventBus:

    def __init__(self):
        self.events = []

    def publish(
        self,
        event: ManufacturingEvent,
    ):
        self.events.append(event)

    def all(self):
        return list(self.events)

    def clear(self):
        self.events.clear()
