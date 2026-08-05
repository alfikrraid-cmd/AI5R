import dataclasses
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from REPOSITORY_ARCHAEOLOGY.scan_statistics import ScanStatistics


def test_scan_statistics_holds_all_fields():
    stats = ScanStatistics(
        files_discovered=10,
        files_ignored_by_extension=3,
        directories_ignored=2,
        symlinks_ignored=1,
    )

    assert stats.files_discovered == 10
    assert stats.files_ignored_by_extension == 3
    assert stats.directories_ignored == 2
    assert stats.symlinks_ignored == 1


def test_scan_statistics_zero_values_are_valid():
    stats = ScanStatistics(
        files_discovered=0,
        files_ignored_by_extension=0,
        directories_ignored=0,
        symlinks_ignored=0,
    )

    assert stats.files_discovered == 0


def test_scan_statistics_is_immutable():
    stats = ScanStatistics(
        files_discovered=0,
        files_ignored_by_extension=0,
        directories_ignored=0,
        symlinks_ignored=0,
    )

    with pytest.raises(dataclasses.FrozenInstanceError):
        stats.files_discovered = 99


@pytest.mark.parametrize(
    "field_name",
    ["files_discovered", "files_ignored_by_extension", "directories_ignored", "symlinks_ignored"],
)
def test_scan_statistics_rejects_negative_values(field_name):
    kwargs = {
        "files_discovered": 0,
        "files_ignored_by_extension": 0,
        "directories_ignored": 0,
        "symlinks_ignored": 0,
    }
    kwargs[field_name] = -1

    with pytest.raises(ValueError):
        ScanStatistics(**kwargs)
