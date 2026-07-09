from dataclasses import dataclass

from SALES.PIPELINE.pipeline_stage import NEW_LEAD, PipelineStage


@dataclass
class SalesOpportunity:
    opportunity_id: str
    customer: str
    value: float
    stage: PipelineStage = NEW_LEAD


class SalesPipeline:
    def __init__(self):
        self._items = {}

    def add(self, opportunity: SalesOpportunity):
        if opportunity.opportunity_id in self._items:
            raise ValueError("Duplicate opportunity")

        self._items[opportunity.opportunity_id] = opportunity

    def move(self, opportunity_id: str, stage: PipelineStage):
        self._items[opportunity_id].stage = stage

    def forecast_value(self):
        return sum(
            item.value * item.stage.probability
            for item in self._items.values()
        )

    def open_value(self):
        return sum(
            item.value
            for item in self._items.values()
            if not item.stage.is_closed
        )

    def won_value(self):
        return sum(
            item.value
            for item in self._items.values()
            if item.stage.code == "WON"
        )

    def lost_value(self):
        return sum(
            item.value
            for item in self._items.values()
            if item.stage.code == "LOST"
        )
