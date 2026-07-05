from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from FACTORY.FOUNDATION.build_report import BuildReport


def test_build_report_creates_json_files(tmp_path):
    report = BuildReport(tmp_path)

    generated = report.write_all(
        {
            "build.json": {
                "status": "SUCCESS",
            },
            "validation.json": {
                "status": "VALID",
            },
        }
    )

    assert len(generated) == 2

    assert (tmp_path / "build.json").exists()

    assert (tmp_path / "validation.json").exists()


def test_build_report_content(tmp_path):
    report = BuildReport(tmp_path)

    report.write(
        "build.json",
        {
            "product": "LTSA-BRAIN",
        },
    )

    data = json.loads(
        (tmp_path / "build.json").read_text()
    )

    assert data["product"] == "LTSA-BRAIN"
