try:
    from .manufacturing_pipeline import ManufacturingPipeline
except ImportError:
    from manufacturing_pipeline import ManufacturingPipeline


class FactoryCompiler:
    """
    Compiles and executes manufacturing definitions through a pipeline.

    `context` is additive (UMR-001, MWO-LTSA-049) -- when a
    ManufacturingContext is supplied, it flows into the pipeline payload so
    any station can read it (UMC-001 Stage 2). Omitting it preserves every
    pre-existing caller's behavior exactly.
    """

    def __init__(self, pipeline: ManufacturingPipeline):
        self.pipeline = pipeline

    def compile(self, definition: dict, context=None) -> dict:
        if "product" not in definition:
            raise ValueError("Manufacturing definition requires product")

        payload = {
            "product": definition["product"],
            "definition": definition,
            "status": "COMPILED",
        }

        if context is not None:
            payload["context"] = context

        result = self.pipeline.run(payload)

        return {
            "status": "FACTORY_COMPILED",
            "product": definition["product"],
            "pipeline": result,
        }
