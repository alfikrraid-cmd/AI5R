from types import MappingProxyType

from .dataset_schema import DatasetSchema
from .detected_enterprise_object import DetectedEnterpriseObjects
from .import_preview import ImportPreview, WorksheetPreview
from .validation_result import ValidationResult


class PreviewEngine:
    """Create deterministic read-only import summaries."""

    __slots__ = ()

    def preview(
        self,
        validation: ValidationResult,
        objects,
        schema,
    ) -> ImportPreview:
        if isinstance(objects, DetectedEnterpriseObjects):
            groups = ((objects, schema),)
        else:
            groups = tuple(zip(objects, schema))

        errors = tuple(
            issue
            for issue in validation.issues
            if issue.severity == "ERROR"
        )
        warnings = tuple(
            issue
            for issue in validation.issues
            if issue.severity == "WARNING"
        )
        worksheets = tuple(
            self._worksheet(
                item_objects,
                item_schema,
                errors,
                warnings,
            )
            for item_objects, item_schema in groups
        )
        return ImportPreview(
            is_valid=validation.is_valid,
            worksheets=worksheets,
            total_estimated_objects=sum(
                item.estimated_imported_objects for item in worksheets
            ),
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def summary(preview: ImportPreview):
        return MappingProxyType(
            {
                "worksheet_count": len(preview.worksheets),
                "document_types": tuple(
                    item.document_type for item in preview.worksheets
                ),
                "detected_object_count": sum(
                    len(item.detected_objects) for item in preview.worksheets
                ),
                "estimated_imported_objects": (
                    preview.total_estimated_objects
                ),
                "error_count": len(preview.errors),
                "warning_count": len(preview.warnings),
            }
        )

    @staticmethod
    def worksheet_preview(
        preview: ImportPreview,
        worksheet_name: str,
    ) -> WorksheetPreview:
        return next(
            item
            for item in preview.worksheets
            if item.worksheet_name == worksheet_name
        )

    def object_preview(
        self,
        preview: ImportPreview,
        worksheet_name: str | None = None,
    ) -> tuple[str, ...]:
        if worksheet_name is not None:
            return self.worksheet_preview(
                preview,
                worksheet_name,
            ).detected_objects
        return tuple(
            object_type
            for worksheet in preview.worksheets
            for object_type in worksheet.detected_objects
        )

    @staticmethod
    def issue_summary(preview: ImportPreview):
        return MappingProxyType(
            {
                "error_count": len(preview.errors),
                "warning_count": len(preview.warnings),
                "error_codes": tuple(
                    issue.code for issue in preview.errors
                ),
                "warning_codes": tuple(
                    issue.code for issue in preview.warnings
                ),
            }
        )

    @staticmethod
    def _worksheet(
        objects: DetectedEnterpriseObjects,
        schema: DatasetSchema,
        errors,
        warnings,
    ) -> WorksheetPreview:
        detected = (
            objects.primary_object,
            *objects.related_objects,
        )
        object_types = tuple(item.object_type for item in detected)
        mapped_columns = tuple(
            sorted(
                {
                    column_index
                    for item in detected
                    for column_index in item.source_columns
                }
            )
        )
        if schema.data_region is None:
            data_row_count = 0
        else:
            start, end = schema.data_region
            data_row_count = end - start + 1

        worksheet_errors = tuple(
            issue
            for issue in errors
            if issue.worksheet_name == schema.worksheet_name
        )
        worksheet_warnings = tuple(
            issue
            for issue in warnings
            if issue.worksheet_name == schema.worksheet_name
        )
        return WorksheetPreview(
            worksheet_name=schema.worksheet_name,
            document_type=objects.document_type,
            detected_objects=object_types,
            is_valid=not worksheet_errors,
            mapped_columns=mapped_columns,
            column_count=schema.column_count,
            data_row_count=data_row_count,
            estimated_imported_objects=(
                data_row_count * len(object_types)
            ),
            error_count=len(worksheet_errors),
            warning_count=len(worksheet_warnings),
        )


__all__ = ["PreviewEngine"]
