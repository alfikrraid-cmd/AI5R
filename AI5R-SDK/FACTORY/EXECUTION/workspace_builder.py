from pathlib import Path
from uuid import uuid4


class WorkspaceBuilder:

    def build(
        self,
        artifacts: list[str],
        output_root: str = "BUILD",
    ) -> dict:

        run_id = f"RUN-{uuid4().hex[:8]}"

        workspace = Path(output_root) / run_id

        workspace.mkdir(parents=True, exist_ok=True)

        created = []

        for artifact in artifacts:

            target = workspace / artifact

            target.parent.mkdir(parents=True, exist_ok=True)

            target.touch(exist_ok=True)

            created.append(str(target))

        return {
            "status": "WORKSPACE_CREATED",
            "run_id": run_id,
            "workspace": str(workspace),
            "artifacts": created,
        }
