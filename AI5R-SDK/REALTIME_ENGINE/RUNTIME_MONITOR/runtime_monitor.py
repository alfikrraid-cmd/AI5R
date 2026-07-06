from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any


@dataclass
class RuntimeMetric:

    metric_type: str
    value: Any
    created_at: str = datetime.now(UTC).isoformat()



class AdaptiveRuntimeMonitor:


    def __init__(self):

        self.metrics = []


    def record(
        self,
        metric_type: str,
        value: Any
    ):

        metric = RuntimeMetric(
            metric_type=metric_type,
            value=value
        )

        self.metrics.append(metric)


        return {
            "status": "RECORDED",
            "metric_type": metric_type
        }



    def health_check(self):

        return {
            "status": "HEALTHY",
            "metrics": len(self.metrics)
        }
