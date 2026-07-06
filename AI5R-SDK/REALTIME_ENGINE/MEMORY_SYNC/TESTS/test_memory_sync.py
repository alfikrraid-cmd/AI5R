from REALTIME_ENGINE.MEMORY_SYNC import (
    RealtimeMemorySynchronizer,
)


def test_memory_sync():


    sync = RealtimeMemorySynchronizer()


    result = sync.store(
        {
            "action": "SEND_REPLY",
            "result": "customer accepted"
        }
    )


    assert result["status"] == "STORED"
    assert result["memory_count"] == 1
