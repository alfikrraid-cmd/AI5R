from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from numbers import Integral, Real

from .dataset_analyzer import DatasetAnalyzer
from .dataset_schema import ColumnSchema, DatasetSchema
from .raw_dataset import RawDataset


class SchemaDetector:
    """Detect worksheet structure without assigning business meaning."""

    __slots__ = ("_analyzer",)

    def __init__(self, analyzer: DatasetAnalyzer | None = None) -> None:
        self._analyzer = analyzer or DatasetAnalyzer()

    def detect(self, dataset: RawDataset) -> tuple[DatasetSchema, ...]:
        analysis = self._analyzer.analyze(dataset)
        analyses = {
            worksheet.worksheet_name: worksheet
            for worksheet in analysis.worksheets
        }
        return tuple(
            self._detect_worksheet(
                worksheet,
                analyses[worksheet["name"]].column_count,
            )
            for worksheet in dataset.data
        )

    def header_row(
        self,
        dataset: RawDataset,
        worksheet_name: str,
    ) -> int | None:
        return self._schema(dataset, worksheet_name).header_row

    def data_region(
        self,
        dataset: RawDataset,
        worksheet_name: str,
    ) -> tuple[int, int] | None:
        return self._schema(dataset, worksheet_name).data_region

    def column_layout(
        self,
        dataset: RawDataset,
        worksheet_name: str,
    ) -> tuple[ColumnSchema, ...]:
        return self._schema(dataset, worksheet_name).columns

    def column_profile(
        self,
        dataset: RawDataset,
        worksheet_name: str,
        column_index: int,
    ) -> ColumnSchema:
        return self.column_layout(dataset, worksheet_name)[column_index]

    def _detect_worksheet(
        self,
        worksheet,
        column_count: int,
    ) -> DatasetSchema:
        rows = worksheet["rows"]
        header_row = self._probable_header_row(rows)
        data_region = self._contiguous_data_region(rows, header_row)
        columns = tuple(
            self._column_schema(
                rows,
                column_index,
                header_row,
                data_region,
            )
            for column_index in range(column_count)
        )
        return DatasetSchema(
            worksheet_name=worksheet["name"],
            header_row=header_row,
            data_region=data_region,
            column_count=column_count,
            columns=columns,
        )

    @classmethod
    def _probable_header_row(cls, rows) -> int | None:
        first = next(
            (
                index
                for index, row in enumerate(rows)
                if not cls._empty_row(row)
            ),
            None,
        )
        if first is None:
            return None

        values = tuple(value for value in rows[first] if value is not None)
        has_data_after = any(
            not cls._empty_row(row) for row in rows[first + 1 :]
        )
        if (
            has_data_after
            and values
            and all(isinstance(value, str) for value in values)
            and len(values) == len(set(values))
        ):
            return first
        return None

    @classmethod
    def _contiguous_data_region(
        cls,
        rows,
        header_row: int | None,
    ) -> tuple[int, int] | None:
        search_start = header_row + 1 if header_row is not None else 0
        start = next(
            (
                index
                for index in range(search_start, len(rows))
                if not cls._empty_row(rows[index])
            ),
            None,
        )
        if start is None:
            return None

        end = start
        for index in range(start + 1, len(rows)):
            if cls._empty_row(rows[index]):
                break
            end = index
        return start, end

    def _column_schema(
        self,
        rows,
        column_index: int,
        header_row: int | None,
        data_region: tuple[int, int] | None,
    ) -> ColumnSchema:
        header = self._cell(rows, header_row, column_index)
        if data_region is None:
            values = ()
        else:
            start, end = data_region
            values = tuple(
                self._cell(rows, row_index, column_index)
                for row_index in range(start, end + 1)
            )
        populated = tuple(value for value in values if value is not None)
        return ColumnSchema(
            column_index=column_index,
            header=header,
            dominant_data_type=self._dominant_type(populated),
            populated_count=len(populated),
            empty_count=len(values) - len(populated),
        )

    @classmethod
    def _dominant_type(cls, values) -> str:
        if not values:
            return "empty"
        types = tuple(cls._structural_type(value) for value in values)
        counts = Counter(types)
        return max(dict.fromkeys(types), key=counts.get)

    @staticmethod
    def _structural_type(value) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, datetime):
            return "datetime"
        if isinstance(value, date):
            return "date"
        if isinstance(value, Integral):
            return "integer"
        if isinstance(value, (Real, Decimal)):
            return "number"
        if isinstance(value, str):
            return "text"
        if isinstance(value, (bytes, bytearray)):
            return "binary"
        return "other"

    @staticmethod
    def _cell(rows, row_index: int | None, column_index: int):
        if row_index is None or column_index >= len(rows[row_index]):
            return None
        return rows[row_index][column_index]

    @staticmethod
    def _empty_row(row) -> bool:
        return all(value is None for value in row)

    def _schema(
        self,
        dataset: RawDataset,
        worksheet_name: str,
    ) -> DatasetSchema:
        return next(
            schema
            for schema in self.detect(dataset)
            if schema.worksheet_name == worksheet_name
        )


__all__ = ["SchemaDetector"]
