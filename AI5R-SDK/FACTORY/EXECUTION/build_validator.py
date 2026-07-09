from pathlib import Path


class BuildValidator:

    def validate(
        self,
        workspace: str,
        required_files: list[str],
    ) -> dict:

        workspace_path = Path(workspace)

        missing = []

        for required in required_files:
            if not (workspace_path / required).exists():
                missing.append(required)

        return {
            "status": (
                "BUILD_VALID"
                if not missing
                else "BUILD_INVALID"
            ),
            "workspace": str(workspace_path),
            "missing_files": missing,
            "validated_files": len(required_files) - len(missing),
            "required_files": len(required_files),
        }
