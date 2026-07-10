from MANUFACTURING_CENTER.manufacturing_parallel_executor import (
    ManufacturingParallelExecutor,
)


def test_execute_level_returns_results() -> None:
    executor = ManufacturingParallelExecutor()

    executed: list[str] = []

    def runner(capability: str) -> str:
        executed.append(capability)
        return capability.lower()

    result = executor.execute_level(
        ("A", "B", "C"),
        runner,
    )

    assert set(executed) == {"A", "B", "C"}
    assert result == {
        "A": "a",
        "B": "b",
        "C": "c",
    }


def test_empty_level_returns_empty_dict() -> None:
    executor = ManufacturingParallelExecutor()

    assert executor.execute_level(tuple(), lambda _: None) == {}
