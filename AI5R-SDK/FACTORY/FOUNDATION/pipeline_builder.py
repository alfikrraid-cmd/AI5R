try:
    from .manufacturing_pipeline import ManufacturingPipeline
    from .station_registry import StationRegistry
except ImportError:
    from manufacturing_pipeline import ManufacturingPipeline
    from station_registry import StationRegistry


class PipelineBuilder:
    """
    Builds a ManufacturingPipeline from registered station names.
    """

    def __init__(self, registry: StationRegistry):
        self.registry = registry

    def build(self, station_names: list) -> ManufacturingPipeline:
        pipeline = ManufacturingPipeline()

        for name in station_names:
            station = self.registry.get(name)
            pipeline.add_station(station)

        return pipeline
