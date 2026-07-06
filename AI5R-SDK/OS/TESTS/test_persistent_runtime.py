from OS import (
    PersistentRuntime,
)


def test_save_snapshot():
    runtime = PersistentRuntime()

    snapshot = runtime.save(
        "MAIN",
        {"cycle": 1},
    )

    assert snapshot.runtime_id == "MAIN"


def test_latest_snapshot():
    runtime = PersistentRuntime()

    runtime.save("MAIN", {"cycle": 1})

    latest = runtime.save(
        "MAIN",
        {"cycle": 2},
    )

    assert runtime.latest("MAIN") is latest


def test_history():
    runtime = PersistentRuntime()

    runtime.save("MAIN", {"a": 1})
    runtime.save("MAIN", {"a": 2})

    assert len(runtime.history("MAIN")) == 2


def test_snapshot_registry():
    runtime = PersistentRuntime()

    runtime.save("MAIN", {"a": 1})

    snapshot = runtime.snapshot()

    assert len(snapshot) == 1
