"""
Compatibility package for architecture validation.

Expose the real AI5R-SDK source directory as AI5R_SDK.__path__
so pkgutil-based scanners can discover SDK modules.
"""

from pathlib import Path

_REAL_SDK_PATH = Path(__file__).resolve().parent.parent / "AI5R-SDK"

__path__ = [str(_REAL_SDK_PATH)]
SDK_NAME = "AI5R_SDK"
