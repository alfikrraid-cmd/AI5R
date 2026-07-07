from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from STUDIO_CONTROL.studio_command_api import (
    StudioCommand,
    StudioCommandAPI,
)


def test_execute_command():
    api = StudioCommandAPI()

    result = api.execute(
        StudioCommand(
            command="RUN_TASK",
            payload={
                "task":"demo",
            },
        )
    )

    assert result["accepted"] is True
    assert result["command"] == "RUN_TASK"
