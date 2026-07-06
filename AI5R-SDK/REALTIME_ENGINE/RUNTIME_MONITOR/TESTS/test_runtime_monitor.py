from REALTIME_ENGINE.RUNTIME_MONITOR import (
    AdaptiveRuntimeMonitor,
)


def test_runtime_monitor():


    monitor = AdaptiveRuntimeMonitor()


    result = monitor.record(
        "EVENT_PROCESSING",
        {
            "success": True
        }
    )


    assert result["status"] == "RECORDED"


    health = monitor.health_check()


    assert health["status"] == "HEALTHY"
    assert health["metrics"] == 1
