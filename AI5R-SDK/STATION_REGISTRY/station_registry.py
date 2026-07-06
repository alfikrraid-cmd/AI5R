from MANUFACTURING_STATION import BaseManufacturingStation


class StationRegistry:
    def __init__(self):
        self._stations = {}

    def register(self, station: BaseManufacturingStation):
        if station is None:
            raise ValueError("station is required")

        station_code = station.station_code

        if not station_code:
            raise ValueError("station_code is required")

        self._stations[station_code] = station

        return {
            "status": "REGISTERED",
            "station_code": station_code,
            "station_name": station.station_name,
        }

    def unregister(self, station_code: str):
        if station_code in self._stations:
            del self._stations[station_code]
            return {
                "status": "UNREGISTERED",
                "station_code": station_code,
            }

        return {
            "status": "NOT_FOUND",
            "station_code": station_code,
        }

    def get(self, station_code: str):
        return self._stations.get(station_code)

    def list(self):
        return [
            {
                "station_code": station.station_code,
                "station_name": station.station_name,
            }
            for station in self._stations.values()
        ]

    def exists(self, station_code: str):
        return station_code in self._stations
