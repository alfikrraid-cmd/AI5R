"""
MWO-LTSA-IMPORT-PROD-DEPENDENCY-001 -- proves requirements.txt (CORE-
SERVICES/BACKEND-API/requirements.txt, the exact file api.Dockerfile
installs from -- `COPY .../requirements.txt /tmp/requirements.txt` then
`pip install --no-cache-dir -r /tmp/requirements.txt`, nothing else) is a
COMPLETE dependency closure for `import main` (main.py's own
`uvicorn main:app` startup, byte for byte).

Root cause this guards against, reproduced directly before being fixed:
excel_reader.py (AI5R-SDK/ENTERPRISE_DATA_ENGINE, imported unconditionally
by that package's own __init__.py, reached from main.py via routers.
import_router -> API.import_cli -> API.import_adapter) does
`import xlrd` and `from openpyxl import load_workbook` at module level --
neither package was listed in requirements.txt, so a real container built
from api.Dockerfile crashed at startup with
`ModuleNotFoundError: No module named 'xlrd'`, never reaching a single
request. The dev/test environment this whole test suite otherwise runs in
already has every such package installed (from a much larger local
venv), so no other test in this codebase would ever catch a gap like
this -- only an install limited to EXACTLY requirements.txt can.

Method: `pip install --target <empty dir> -r requirements.txt` (a real
install, not a mock) into an otherwise-empty directory, then a real `-S`
(no automatic `site` import -- skips this venv's own, much larger,
site-packages) subprocess with PYTHONPATH pointing ONLY at that directory,
importing main.py exactly as the real CMD would. Proven, not assumed, to
actually fail the same way the real bug did: reverting requirements.txt to
its pre-fix content (fastapi/uvicorn[standard]/python-multipart only) and
re-running this exact method reproduces the identical
`ModuleNotFoundError: No module named 'xlrd'` this test would have caught.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

_BACKEND_API_DIR = Path(__file__).resolve().parents[1]
_REQUIREMENTS = _BACKEND_API_DIR / "requirements.txt"


def test_requirements_txt_is_a_complete_dependency_closure_for_importing_main(tmp_path):
    target = tmp_path / "site-packages"
    install = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet", "--target", str(target), "-r", str(_REQUIREMENTS)],
        capture_output=True,
        text=True,
    )
    assert install.returncode == 0, f"pip install -r requirements.txt itself failed:\n{install.stderr}"

    # -S: skip the `site` module, so THIS test-runner's own (much larger)
    # venv site-packages is never on sys.path -- only PYTHONPATH's fresh,
    # requirements.txt-only install directory is. SYSTEMROOT is passed
    # through because Windows' own socket/SSL machinery needs it to
    # initialize at all; it carries no Python packages.
    env = {"PYTHONPATH": str(target), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    result = subprocess.run(
        [sys.executable, "-S", "-c", "import main; print('IMPORT_OK')"],
        cwd=str(_BACKEND_API_DIR),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        f"`import main` failed using ONLY requirements.txt's own dependencies "
        f"-- api.Dockerfile's real container would crash at startup the same way:\n"
        f"{result.stderr}"
    )
    assert "IMPORT_OK" in result.stdout
