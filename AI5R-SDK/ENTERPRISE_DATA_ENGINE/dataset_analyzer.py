from .dataset_analysis import DatasetAnalysis, WorksheetAnalysis
from .raw_dataset import RawDataset


class DatasetAnalyzer:
    """Compute structural counts without interpreting dataset values."""

    __slots__ = ()

    def analyze(self, dataset: RawDataset) -> DatasetAnalysis:
        worksheets = tuple(
            self._analyze_worksheet(worksheet) for worksheet in dataset.data
        )
        statistics = self._sum_statistics(worksheets)
        return DatasetAnalysis(
            worksheets=worksheets,
            worksheet_count=len(worksheets),
            row_count=sum(item.row_count for item in worksheets),
            column_count=sum(item.column_count for item in worksheets),
            empty_row_count=sum(item.empty_row_count for item in worksheets),
            empty_column_count=sum(
                item.empty_column_count for item in worksheets
            ),
            cell_statistics=statistics,
        )

    def worksheet_count(self, dataset: RawDataset) -> int:
        return self.analyze(dataset).worksheet_count

    def row_count(
        self,
        dataset: RawDataset,
        worksheet_name: str | None = None,
    ) -> int:
        analysis = self.analyze(dataset)
        return self._select(analysis, worksheet_name, "row_count")

    def column_count(
        self,
        dataset: RawDataset,
        worksheet_name: str | None = None,
    ) -> int:
        analysis = self.analyze(dataset)
        return self._select(analysis, worksheet_name, "column_count")

    def empty_row_count(
        self,
        dataset: RawDataset,
        worksheet_name: str | None = None,
    ) -> int:
        analysis = self.analyze(dataset)
        return self._select(analysis, worksheet_name, "empty_row_count")

    def empty_column_count(
        self,
        dataset: RawDataset,
        worksheet_name: str | None = None,
    ) -> int:
        analysis = self.analyze(dataset)
        return self._select(analysis, worksheet_name, "empty_column_count")

    def cell_statistics(
        self,
        dataset: RawDataset,
        worksheet_name: str | None = None,
    ):
        analysis = self.analyze(dataset)
        if worksheet_name is None:
            return analysis.cell_statistics
        return self._worksheet(analysis, worksheet_name).cell_statistics

    @staticmethod
    def _analyze_worksheet(worksheet) -> WorksheetAnalysis:
        rows = worksheet["rows"]
        row_count = len(rows)
        column_count = max((len(row) for row in rows), default=0)
        empty_row_count = sum(
            all(
                column >= len(row) or row[column] is None
                for column in range(column_count)
            )
            for row in rows
        )
        empty_column_count = sum(
            all(
                column >= len(row) or row[column] is None
                for row in rows
            )
            for column in range(column_count)
        )
        total_cells = row_count * column_count
        populated_cells = sum(
            value is not None for row in rows for value in row
        )
        return WorksheetAnalysis(
            worksheet_name=worksheet["name"],
            row_count=row_count,
            column_count=column_count,
            empty_row_count=empty_row_count,
            empty_column_count=empty_column_count,
            cell_statistics={
                "total_cells": total_cells,
                "populated_cells": populated_cells,
                "empty_cells": total_cells - populated_cells,
            },
        )

    @staticmethod
    def _sum_statistics(worksheets):
        return {
            name: sum(
                worksheet.cell_statistics[name] for worksheet in worksheets
            )
            for name in ("total_cells", "populated_cells", "empty_cells")
        }

    @staticmethod
    def _worksheet(
        analysis: DatasetAnalysis,
        worksheet_name: str,
    ) -> WorksheetAnalysis:
        return next(
            item
            for item in analysis.worksheets
            if item.worksheet_name == worksheet_name
        )

    def _select(
        self,
        analysis: DatasetAnalysis,
        worksheet_name: str | None,
        field_name: str,
    ) -> int:
        if worksheet_name is None:
            return getattr(analysis, field_name)
        return getattr(self._worksheet(analysis, worksheet_name), field_name)


__all__ = ["DatasetAnalyzer"]
