try:
    from .manufacturing_event import ManufacturingEvent
except ImportError:
    from manufacturing_event import ManufacturingEvent


class ManufacturingPipeline:
    """
    Executes manufacturing stations in sequence.

    Reused as part of UMR-001 (Universal Manufacturing Runtime, MWO-LTSA-049).
    `station_events` is additive -- per-station completion events, in the
    same FOUNDATION.ManufacturingEvent shape ManufacturingRuntime already
    uses for its own BUILD_STARTED/BUILD_COMPLETED events -- closing UMC-001
    Stage 7 (Event Publication)'s wiring gap without altering `run()`'s
    signature or any existing return key.
    """

    def __init__(self):
        self.stations = []

    def add_station(self, station):
        self.stations.append(station)
        return self

    def run(self, payload: dict) -> dict:
        result = payload

        history = []
        station_events = []

        build_id = str(
            payload.get("build_id")
            or payload.get("definition", {}).get("build_id", "UNKNOWN")
        )
        product = str(
            payload.get("product")
            or payload.get("definition", {}).get("product", "UNKNOWN")
        )

        for station in self.stations:
            result = station.run(result)

            station_name = station.__class__.__name__

            history.append({
                "station": station_name,
                "status": result.get("status"),
            })

            station_events.append(
                ManufacturingEvent(
                    event_type="STATION_COMPLETED",
                    station=station_name,
                    build_id=build_id,
                    product=product,
                    payload={"status": result.get("status")},
                ).to_dict()
            )

        return {
            "status": "PIPELINE_COMPLETED",
            "result": result,
            "history": history,
            "station_events": station_events,
        }
