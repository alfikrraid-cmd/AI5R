"""
MWO-LTSA-HISTORICAL-INGESTION-DEPENDENCY-001 -- proves requirements.txt
(CORE-SERVICES/BACKEND-API/requirements.txt, the exact file api.Dockerfile
installs from) is a COMPLETE dependency closure for the historical PM/CM
ingestion CLI entry point (PRODUCTS/LTSA-BRAIN/INGESTION/
historical_pm_cmon_cli.py's own `if __name__ == "__main__": main()`),
the same guarantee test_requirements_dependency_closure.py already proves
for `import main` (the live API's own entry point) -- extended here to
this second, independent entry point, not folded into that test, since
the two have genuinely different import graphs and this repo has no
single "install everything" requirements file that covers both.

Root cause this guards against, reproduced directly before being fixed:
historical_pm_cmon_cli.py -> historical_pm_cmon_orchestrator.py ->
historical_pm_cmon_extraction.py does `import pdfplumber` at module
level. pdfplumber is not listed in requirements.txt, so running this CLI
in any environment built strictly from requirements.txt (a real container
built from api.Dockerfile, or any other "clean install") fails at import
time with `ModuleNotFoundError: No module named 'pdfplumber'`, before
argparse even runs -- "Historical PM/CM ingestion fails in a clean
environment." Confirmed reachable ONLY via this CLI: the live FastAPI app
(main.py/dependencies.py) does not import historical_pm_cmon_orchestrator
or historical_pm_cmon_extraction anywhere -- historical_review.py's
router only reaches historical_pm_cmon_staging_repository.py and
historical_pm_cmon_promotion_service.py, neither of which touches
pdfplumber -- so this specific gap does NOT affect the running API; it
affects only the ingestion CLI's own dry-run/stage commands.

Method: identical to test_requirements_dependency_closure.py --
`pip install --target <empty dir> -r requirements.txt` (a real install),
then a real `-S` subprocess (skips this test-runner's own, much larger,
venv) with PYTHONPATH pointing ONLY at that fresh install directory,
importing historical_pm_cmon_cli from its own directory exactly as the
real CLI invocation would (cwd=INGESTION_DIR, matching how its sibling
modules like ltsa_pump_inventory_db_upsert are imported as bare top-level
names, not package-qualified).
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

_BACKEND_API_DIR = Path(__file__).resolve().parents[1]
_REQUIREMENTS = _BACKEND_API_DIR / "requirements.txt"
_INGESTION_DIR = _BACKEND_API_DIR.parent.parent / "PRODUCTS" / "LTSA-BRAIN" / "INGESTION"


def test_requirements_txt_is_a_complete_dependency_closure_for_historical_ingestion_cli(tmp_path):
    target = tmp_path / "site-packages"
    install = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--target", str(target), "-r", str(_REQUIREMENTS)],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, f"pip install -r requirements.txt itself failed:\n{install.stderr}"
    env = {"PYTHONPATH": str(target), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    result = subprocess.run(
        [sys.executable, "-S", "-c", "import historical_pm_cmon_cli; print('IMPORT_OK')"],
        cwd=str(_INGESTION_DIR),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"`import historical_pm_cmon_cli` failed using ONLY requirements.txt's own "
        f"dependencies -- running the real historical PM/CM ingestion CLI in any "
        f"clean environment (a container built from api.Dockerfile, a fresh venv, "
        f"CI) would fail the same way:\n{result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout
