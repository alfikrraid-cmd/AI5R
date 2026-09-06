"""AI5R-PHASE4E5, Section G -- Excel end-to-end UAT using the ACTUAL
template/parse production code (not a hand-rolled substitute): builds a
representative workbook via openpyxl (the same library
build_pm_schedule_import_template()/parse_xlsx_grid() both use), covering
every fixture requirement the mission lists, parses it through the real
parse_xlsx_grid(), and proves the resulting {headers, rows} grid is
exactly what utils/pmExcelImport.js's buildImportPreview() (the
client-side mapping/validation layer) expects to consume. The JS-side
half of this round trip -- mapping this exact grid into Bulk Editor rows
-- is proven by
AI5R-STUDIO/dashboard/src/modules/ltsa/utils/pmExcelImport.e2eUat.test.js,
which hardcodes the identical grid shape asserted here."""

import sys
from pathlib import Path

from openpyxl import Workbook

CORE_SERVICES_PATH = Path(__file__).resolve().parents[2]
if str(CORE_SERVICES_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_SERVICES_PATH))

from API.pm_schedule_excel_import import parse_xlsx_grid  # noqa: E402
from API.pm_schedule_excel_template import TEMPLATE_COLUMNS, build_pm_schedule_import_template  # noqa: E402


def _uat_workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(TEMPLATE_COLUMNS))
    # Section G's own fixture list, one representative row per bullet.
    sheet.append(["211-P-1A", "MONTHLY", "2026-11-01", "Flushing Line DE; Cooler DE; Cooling Water Cooler DE; Reservoir General", "Sari Wulandari", "2", "exact pump"])
    sheet.append(["110P12B", "MONTHLY", "2026-11-01", "", "", "", "normalized pump"])
    sheet.append(["211-P-1B", "Harian", "2026-11-02", "", "", "", "DAILY alias"])
    sheet.append(["211-P-1B", "Mingguan", "2026-11-03", "", "", "", "WEEKLY alias"])
    sheet.append(["211-P-1B", "Bulanan", "2026-11-04", "", "", "", "MONTHLY alias"])
    sheet.append(["211-P-1B", "Runtime Based", "2026-11-05", "", "", "", "RUNTIME_BASED alias"])
    buffer_bytes = _save(workbook)
    return buffer_bytes


def _invalid_uat_workbook_bytes() -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(list(TEMPLATE_COLUMNS))
    sheet.append(["999-P-XYZ", "MONTHLY", "2026-11-01", "", "", "", "unknown pump"])
    sheet.append(["211-P-1A", "MONTHLY", "09/10/26", "", "", "", "ambiguous date"])
    sheet.append(["211-P-1A", "3 Monthly", "2026-11-01", "", "", "", "invalid frequency"])
    sheet.append(["211-P-1A", "MONTHLY", "2026-11-02", "Reservoir DE", "", "", "Reservoir DE"])
    sheet.append(["211-P-1A", "MONTHLY", "2026-11-03", "Made Up Activity", "", "", "unknown activity"])
    sheet.append(["110P12B", "MONTHLY", "2026-11-04", "", "", "", "duplicate-after-normalization row 1"])
    sheet.append(["110-P-12B", "MONTHLY", "2026-11-04", "", "", "", "duplicate-after-normalization row 2"])
    return _save(workbook)


def _save(workbook) -> bytes:
    import io

    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def test_template_generated_by_actual_code_round_trips_through_actual_parser():
    template_bytes = build_pm_schedule_import_template()
    grid = parse_xlsx_grid(template_bytes)
    assert grid["headers"] == list(TEMPLATE_COLUMNS)
    assert grid["rows"] == []  # the real template ships with zero data rows


def test_uat_fixture_parses_with_every_required_scenario_present():
    grid = parse_xlsx_grid(_uat_workbook_bytes())
    assert grid["row_count"] == 6

    exact_pump_row = grid["rows"][0]
    assert exact_pump_row[0] == "211-P-1A"
    assert exact_pump_row[3] == "Flushing Line DE; Cooler DE; Cooling Water Cooler DE; Reservoir General"

    assert grid["rows"][1][0] == "110P12B"  # raw compact form -- resolved client-side
    assert grid["rows"][2][1] == "Harian"
    assert grid["rows"][3][1] == "Mingguan"
    assert grid["rows"][4][1] == "Bulanan"
    assert grid["rows"][5][1] == "Runtime Based"


def test_invalid_uat_fixture_rows_all_survive_decode_none_dropped():
    # Section J/G -- decode-only: the backend never classifies a row as
    # invalid or drops it; every data row present in the workbook comes
    # back in the grid for the frontend to classify.
    grid = parse_xlsx_grid(_invalid_uat_workbook_bytes())
    assert grid["row_count"] == 7
    assert [row[0] for row in grid["rows"]] == [
        "999-P-XYZ", "211-P-1A", "211-P-1A", "211-P-1A", "211-P-1A", "110P12B", "110-P-12B",
    ]
