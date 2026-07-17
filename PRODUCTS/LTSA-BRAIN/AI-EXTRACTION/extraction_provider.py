"""ExtractionProvider -- the AI Extraction Capability's provider interface.

Per Chief Architect ruling on the Document Upload MVP: "Claude is the first
provider, not the architecture... Keep provider-specific code isolated...
Return a normalized JSON structure... Make it possible to add other
providers later without changing the LTSA workflow." Every provider
implements this one method and returns the normalized ExtractionResult
(models.py); the n8n workflow -- via cli.py -- never depends on which
provider ran.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from models import ExtractionResult


class ExtractionProvider(ABC):
    @abstractmethod
    def extract(self, file_path: Path, mime_type: str) -> ExtractionResult:
        """Perform OCR + document-type detection + field extraction on one file.

        Args:
            file_path: path to an already-uploaded, temporary file. The
                provider reads it but never persists a copy of it --
                original-file storage is out of scope for this capability
                (deferred to a future Platform Storage MWO).
            mime_type: one of "application/pdf", "image/jpeg", "image/png".
        """
