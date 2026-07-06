import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from ARCHITECTURE import (
    BootTask,
    KernelBootManager,
)


def test_boot_executes_registered_tasks():
    history = []

    manager = KernelBootManager()

    manager.register(
        BootTask(
            "memory",
            lambda: history.append("memory"),
        )
    )

    manager.register(
        BootTask(
            "knowledge",
            lambda: history.append("knowledge"),
        )
    )

    result = manager.boot()

    assert history == [
        "memory",
        "knowledge",
    ]

    assert result.executed_tasks == [
        "memory",
        "knowledge",
    ]


def test_empty_boot():
    manager = KernelBootManager()

    result = manager.boot()

    assert result.executed_tasks == []
    assert result.started_at
    assert result.finished_at
