from dataclasses import dataclass
from typing import Any


@dataclass
class StationDefinition:
    station_code: str
    station_name: str
    input_object: str
    output_object: str
    event_type: str
    version: str
    owner: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "station_code": self.station_code,
            "station_name": self.station_name,
            "input_object": self.input_object,
            "output_object": self.output_object,
            "event_type": self.event_type,
            "version": self.version,
            "owner": self.owner,
        }


class StationRegistry:
    def __init__(self):
        self._stations: dict[str, StationDefinition] = {}

    def register(self, station: StationDefinition) -> None:
        if not station.station_code:
            raise ValueError("Station code is required")

        self._stations[station.station_code] = station

    def get(self, station_code: str) -> StationDefinition:
        if station_code not in self._stations:
            raise KeyError(f"Station not registered: {station_code}")

        return self._stations[station_code]

    def all(self) -> list[StationDefinition]:
        return list(self._stations.values())

    def count(self) -> int:
        return len(self._stations)
