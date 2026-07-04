from .enterprise_cognitive_pipeline import EnterpriseCognitivePipeline


class EnterpriseBrainRuntime:
    """
    Runtime wrapper for Enterprise Cognitive Pipeline.

    Responsibilities:
    - Accept Reality Object
    - Run Enterprise Cognitive Pipeline
    - Return final Learning Object and full cognitive trace
    """

    def __init__(self):
        self.pipeline = EnterpriseCognitivePipeline()

    def run(self, reality):
        result = self.pipeline.run(reality)

        return {
            "status": "completed",
            "runtime": "enterprise_brain_runtime",
            "digital_thread_id": reality.get("object_id", ""),
            "final_stage": "learning",
            "learning": result["learning"],
            "trace": result,
        }
