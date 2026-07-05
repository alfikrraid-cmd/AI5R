from pathlib import Path


class BuildWorkspace:
    """
    Creates canonical manufacturing workspace directories.
    """

    DIRECTORIES = [
        "INPUT",
        "OUTPUT",
        "REPORT",
        "LOG",
        "ARTIFACT",
        "FREEZE",
    ]

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def create(self) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)

        paths = {}

        for directory in self.DIRECTORIES:
            path = self.root / directory
            path.mkdir(parents=True, exist_ok=True)
            paths[directory] = str(path)

        return {
            "status": "WORKSPACE_CREATED",
            "root": str(self.root),
            "paths": paths,
        }

    def path(self, name: str) -> Path:
        if name not in self.DIRECTORIES:
            raise ValueError(f"Unknown workspace directory: {name}")

        return self.root / name
