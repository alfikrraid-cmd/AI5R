"""DrawingExtractionProvider -- the Engineering Drawing extraction
capability's provider interface (Drawing-R5B).

Mirrors ExtractionProvider's own discipline exactly (extraction_provider.py):
one abstract extract() method, provider-specific SDK code isolated to the
concrete implementation file, a normalized result the caller never needs
to branch on by provider. The one deliberate difference: this interface
takes raw file BYTES, not a file_path -- Drawing-R5A0's own storage audit
found no existing "retrieve bytes for a knowledge_source_id" mechanism
(MinIO is provisioned but has zero application-code client usage anywhere
in this repository today), so this adapter must not assume a local temp
file exists. DrawingSourceBytesProvider below is the narrow boundary that
isolates "how do we get the bytes" from "how do we extract from them" --
Drawing-R5B implements ONLY the extraction side; a MinIO-backed
DrawingSourceBytesProvider is explicitly out of scope here (see this
module's own README note in the R5B mission report) and belongs to a
later phase once real upload/download code is built.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from drawing_extraction_models import DrawingExtractionResult


class DrawingExtractionProvider(ABC):
    @abstractmethod
    def extract(self, file_bytes: bytes, mime_type: str) -> DrawingExtractionResult:
        """Perform OCR + engineering-drawing candidate extraction on one
        already-retrieved file's raw bytes.

        Args:
            file_bytes: the file's own raw bytes -- the CALLER is
                responsible for retrieving them (see
                DrawingSourceBytesProvider below); this method never
                reads a filesystem path or a knowledge_source_id itself.
            mime_type: one of drawing_extraction_models.SUPPORTED_MIME_TYPES.
        """


class DrawingSourceBytesProvider(Protocol):
    """Narrow byte-retrieval boundary (R5B Section 4) -- deliberately NOT
    MinIO-specific. A caller supplies any implementation of this single
    method (a MinIO-backed one, a local-filesystem one for tests, or an
    in-memory fake); the Drawing extraction orchestration (see
    CORE-SERVICES/API/engineering_drawing_extraction_staging_service.py)
    never imports MinIO or any storage SDK directly."""

    def get_bytes(self, knowledge_source_id: str) -> tuple[bytes, str]:
        """Returns (file_bytes, mime_type) for an already-registered
        knowledge_source_registry row. Raises if the source cannot be
        retrieved -- never returns empty bytes as if that were valid
        content."""
        ...
