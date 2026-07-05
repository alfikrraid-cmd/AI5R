from dataclasses import dataclass, field


@dataclass
class ManufacturingContext:
    """
    Canonical context flowing through every manufacturing station.
    """

    build_id: str

    product: str

    version: str

    manifest: dict = field(default_factory=dict)

    enterprise_thread: str | None = None

    generated_assets: list = field(default_factory=list)

    validation_report: dict = field(default_factory=dict)

    reports: dict = field(default_factory=dict)

    metadata: dict = field(default_factory=dict)

    frozen: bool = False

    def add_asset(self, asset):
        self.generated_assets.append(asset)

    def add_report(self, name: str, report):
        self.reports[name] = report

    def freeze(self):
        self.frozen = True
