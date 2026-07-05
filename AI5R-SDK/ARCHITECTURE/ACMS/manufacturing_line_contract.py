from dataclasses import dataclass, field


@dataclass(frozen=True)
class ManufacturingLineContract:
    line_code: str
    line_name: str
    input_object: str
    output_object: str
    stations: list[str] = field(default_factory=list)
    runtime: str = "CanonicalRuntime"
    registry: str = "CanonicalRegistry"
    version: str = "1.0"

    def validate(self) -> bool:
        if not self.line_code:
            raise ValueError("line_code is required")

        if not self.line_name:
            raise ValueError("line_name is required")

        if not self.input_object:
            raise ValueError("input_object is required")

        if not self.output_object:
            raise ValueError("output_object is required")

        if not self.stations:
            raise ValueError("stations are required")

        if not self.runtime:
            raise ValueError("runtime is required")

        if not self.registry:
            raise ValueError("registry is required")

        return True

    def station_count(self) -> int:
        return len(self.stations)

    def to_dict(self) -> dict:
        self.validate()

        return {
            "line_code": self.line_code,
            "line_name": self.line_name,
            "input_object": self.input_object,
            "output_object": self.output_object,
            "stations": self.stations,
            "runtime": self.runtime,
            "registry": self.registry,
            "version": self.version,
        }
