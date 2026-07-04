class EnterprisePipeline:
    """
    Enterprise Manufacturing Pipeline

    Execute every Station sequentially.
    """

    def __init__(self):
        self._stations = []

    def add_station(self, station):
        self._stations.append(station)

    def execute(self, enterprise_object):

        current = enterprise_object

        for station in self._stations:

            if hasattr(station, "execute"):
                current = station.execute(current)

            elif hasattr(station, "ingest"):
                current = station.ingest(**current)

            elif hasattr(station, "process"):
                current = station.process(current)

            elif hasattr(station, "adapt"):
                current = station.adapt(current)

            else:
                raise RuntimeError(
                    f"Unknown station interface: {station.__class__.__name__}"
                )

        return current
