class ManufacturingPipeline:
    """
    Executes manufacturing stations in sequence.
    """

    def __init__(self):
        self.stations = []

    def add_station(self, station):
        self.stations.append(station)
        return self

    def run(self, payload: dict) -> dict:
        result = payload

        history = []

        for station in self.stations:
            result = station.run(result)

            history.append({
                "station": station.__class__.__name__,
                "status": result.get("status"),
            })

        return {
            "status": "PIPELINE_COMPLETED",
            "result": result,
            "history": history,
        }
