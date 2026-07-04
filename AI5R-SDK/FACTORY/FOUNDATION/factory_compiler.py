try:
    from .manufacturing_pipeline import ManufacturingPipeline
except ImportError:
    from manufacturing_pipeline import ManufacturingPipeline


class FactoryCompiler:
    """
    Compiles and executes manufacturing definitions through a pipeline.
    """

    def __init__(self, pipeline: ManufacturingPipeline):
        self.pipeline = pipeline

    def compile(self, definition: dict) -> dict:
        if "product" not in definition:
            raise ValueError("Manufacturing definition requires product")

        payload = {
            "product": definition["product"],
            "definition": definition,
            "status": "COMPILED",
        }

        result = self.pipeline.run(payload)

        return {
            "status": "FACTORY_COMPILED",
            "product": definition["product"],
            "pipeline": result,
        }
