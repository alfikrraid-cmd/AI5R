from pathlib import Path


class ArtifactWriter:
    def write(
        self,
        workspace: str,
        artifact_path: str,
        content: str,
    ) -> dict:
        target = Path(workspace) / artifact_path

        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(content, encoding="utf-8")

        return {
            "status": "ARTIFACT_WRITTEN",
            "path": str(target),
            "artifact_path": artifact_path,
            "bytes": len(content.encode("utf-8")),
        }
