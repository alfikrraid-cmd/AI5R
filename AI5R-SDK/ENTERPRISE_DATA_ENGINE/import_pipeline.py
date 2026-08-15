from .import_error import ImportError
from .import_result import ImportResult
from .reader import Reader
from .source_descriptor import SourceDescriptor


class ImportPipeline:
    """Orchestrate raw data imports through explicitly registered readers."""

    def __init__(self) -> None:
        self._readers: dict[str, Reader] = {}

    def register_reader(self, name: str, reader: Reader) -> None:
        if not isinstance(reader, Reader):
            raise ImportError(
                code="INVALID_READER",
                message="Reader must implement the canonical Reader contract",
            )
        if name in self._readers:
            raise ImportError(
                code="DUPLICATE_READER",
                message=f"Reader already registered: {name}",
            )
        self._readers[name] = reader

    def unregister_reader(self, name: str) -> None:
        self._readers.pop(name, None)

    def available_readers(self) -> tuple[str, ...]:
        return tuple(sorted(self._readers))

    def import_data(self, source: SourceDescriptor) -> ImportResult:
        reader = self._readers.get(source.reader_name)
        if reader is None:
            raise ImportError(
                code="UNKNOWN_READER",
                message=f"Reader is not registered: {source.reader_name}",
            )
        if not reader.supports(source):
            raise ImportError(
                code="UNSUPPORTED_SOURCE",
                message=f"Reader does not support source: {source.source_id}",
            )

        dataset = reader.read(source)
        return ImportResult(
            source=source,
            reader_name=source.reader_name,
            dataset=dataset,
        )


__all__ = ["ImportPipeline"]