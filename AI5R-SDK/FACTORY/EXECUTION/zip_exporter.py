from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


class ZipExporter:
    def export(
        self,
        workspace: str,
        output_path: str | None = None,
    ) -> dict:
        workspace_path = Path(workspace)

        if not workspace_path.exists():
            raise ValueError("workspace does not exist")

        if output_path is None:
            output_path = str(workspace_path) + ".zip"

        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        files = [
            path
            for path in workspace_path.rglob("*")
            if path.is_file()
        ]

        with ZipFile(output, "w", ZIP_DEFLATED) as zip_file:
            for path in files:
                zip_file.write(
                    path,
                    arcname=path.relative_to(workspace_path),
                )

        return {
            "status": "ZIP_EXPORTED",
            "workspace": str(workspace_path),
            "zip_path": str(output),
            "file_count": len(files),
        }
