import re
import unicodedata

from .column_mapping import ColumnMapping, DatasetColumnMapping
from .dataset_schema import DatasetSchema


class ColumnMapper:
    """Assign generic semantic labels from structural column headers."""

    __slots__ = ()

    _ALIASES = (
        ("Email", ("email", "e mail", "surel")),
        (
            "Phone",
            (
                "phone",
                "telephone",
                "telepon",
                "nomor telepon",
                "no hp",
                "mobile",
            ),
        ),
        ("Address", ("address", "alamat")),
        ("Date", ("date", "tanggal", "tgl")),
        (
            "Description",
            ("description", "deskripsi", "keterangan", "uraian", "notes", "catatan"),
        ),
        ("Amount", ("amount", "nominal", "nilai", "jumlah")),
        ("Quantity", ("quantity", "qty", "kuantitas")),
        ("Code", ("code", "kode", "sku")),
        ("Name", ("name", "nama")),
        (
            "Identifier",
            ("id", "identifier", "uuid", "number", "nomor"),
        ),
    )

    def map_columns(self, schema):
        if isinstance(schema, DatasetSchema):
            return self._map_dataset(schema)
        return tuple(self._map_dataset(item) for item in schema)

    def mapping_confidence(
        self,
        mapping: ColumnMapping | DatasetColumnMapping,
    ) -> float:
        if isinstance(mapping, ColumnMapping):
            return mapping.confidence
        if not mapping.mappings:
            return 0.0
        return sum(item.confidence for item in mapping.mappings) / len(
            mapping.mappings
        )

    @staticmethod
    def unknown_columns(
        mapping: DatasetColumnMapping,
    ) -> tuple[ColumnMapping, ...]:
        return tuple(
            item
            for item in mapping.mappings
            if item.semantic_label == "Unknown"
        )

    @staticmethod
    def mapped_columns(
        mapping: DatasetColumnMapping,
    ) -> tuple[ColumnMapping, ...]:
        return tuple(
            item
            for item in mapping.mappings
            if item.semantic_label != "Unknown"
        )

    def _map_dataset(self, schema: DatasetSchema) -> DatasetColumnMapping:
        return DatasetColumnMapping(
            worksheet_name=schema.worksheet_name,
            mappings=tuple(
                self._map_column(column.column_index, column.header)
                for column in schema.columns
            ),
        )

    def _map_column(self, column_index: int, header) -> ColumnMapping:
        normalized = self._normalize(header)
        if normalized:
            for label, aliases in self._ALIASES:
                if normalized in aliases:
                    return ColumnMapping(
                        column_index=column_index,
                        source_header=header,
                        semantic_label=label,
                        confidence=1.0,
                    )

            padded = f" {normalized} "
            for label, aliases in self._ALIASES:
                if any(f" {alias} " in padded for alias in aliases):
                    return ColumnMapping(
                        column_index=column_index,
                        source_header=header,
                        semantic_label=label,
                        confidence=0.85,
                    )

        return ColumnMapping(
            column_index=column_index,
            source_header=header,
            semantic_label="Unknown",
            confidence=0.0,
        )

    @staticmethod
    def _normalize(header) -> str:
        if not isinstance(header, str):
            return ""
        decomposed = unicodedata.normalize("NFKD", header)
        without_marks = "".join(
            character
            for character in decomposed
            if not unicodedata.combining(character)
        )
        return re.sub(
            r"[^a-z0-9]+",
            " ",
            without_marks.casefold(),
        ).strip()


__all__ = ["ColumnMapper"]
