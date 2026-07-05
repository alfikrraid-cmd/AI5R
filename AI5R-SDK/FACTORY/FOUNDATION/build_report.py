import json
from pathlib import Path


class BuildReport:
    """
    Writes canonical manufacturing reports.
    """

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, filename: str, data: dict) -> Path:
        path = self.output_dir / filename

        path.write_text(
            json.dumps(
                data,
                indent=2,
                sort_keys=True,
            )
        )

        return path

    def write_all(self, reports: dict) -> list[Path]:
        generated = []

        for filename, data in reports.items():
            generated.append(
                self.write(
                    filename,
                    data,
                )
            )

        return generated
