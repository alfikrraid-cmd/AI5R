from collections import Counter

from .column_mapping import DatasetColumnMapping
from .dataset_schema import DatasetSchema
from .detected_enterprise_object import DetectedEnterpriseObjects
from .validation_result import ValidationIssue, ValidationResult


class ValidationEngine:
    """Validate structural consistency without applying domain rules."""

    __slots__ = ()

    _REQUIRED_LABELS = {
        "Unknown": (),
        "BankTransaction": ("Date", "Amount"),
        "Journal": (),
        "GeneralLedger": (),
        "TrialBalance": (),
        "Invoice": ("Amount",),
        "Customer": ("Name",),
        "Vendor": ("Name",),
        "InventoryItem": ("Quantity",),
        "Equipment": ("Name",),
        "Employee": ("Name",),
        "Payroll": ("Amount",),
    }

    def validate(self, objects, schema, mapping) -> ValidationResult:
        if isinstance(objects, DetectedEnterpriseObjects):
            groups = ((objects, schema, mapping),)
        else:
            groups = tuple(zip(objects, schema, mapping))

        issues = tuple(
            issue
            for item_objects, item_schema, item_mapping in groups
            for issue in self._validate_worksheet(
                item_objects,
                item_schema,
                item_mapping,
            )
        )
        return ValidationResult(
            is_valid=not any(issue.severity == "ERROR" for issue in issues),
            issues=issues,
            worksheet_count=len(groups),
        )

    @staticmethod
    def errors(result: ValidationResult) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue for issue in result.issues if issue.severity == "ERROR"
        )

    @staticmethod
    def warnings(result: ValidationResult) -> tuple[ValidationIssue, ...]:
        return tuple(
            issue for issue in result.issues if issue.severity == "WARNING"
        )

    @staticmethod
    def is_valid(result: ValidationResult) -> bool:
        return result.is_valid

    def _validate_worksheet(
        self,
        objects: DetectedEnterpriseObjects,
        schema: DatasetSchema,
        mapping: DatasetColumnMapping,
    ) -> tuple[ValidationIssue, ...]:
        issues = []
        worksheet_name = schema.worksheet_name

        if (
            objects.worksheet_name != worksheet_name
            or mapping.worksheet_name != worksheet_name
        ):
            issues.append(
                self._error(
                    "WORKSHEET_MISMATCH",
                    "Object, schema, and mapping worksheets must match",
                    worksheet_name,
                )
            )

        schema_indices = tuple(
            column.column_index for column in schema.columns
        )
        mapping_indices = tuple(
            column.column_index for column in mapping.mappings
        )
        schema_index_set = frozenset(schema_indices)
        mappings_by_index = {
            column.column_index: column for column in mapping.mappings
        }

        if schema.column_count != len(schema.columns):
            issues.append(
                self._error(
                    "COLUMN_COUNT_MISMATCH",
                    "Schema column count does not match its column layout",
                    worksheet_name,
                )
            )

        for column_index in sorted(schema_index_set - frozenset(mapping_indices)):
            issues.append(
                self._error(
                    "MISSING_COLUMN_MAPPING",
                    "A schema column has no column mapping",
                    worksheet_name,
                    column_index,
                )
            )

        for column_index, count in sorted(Counter(mapping_indices).items()):
            if count > 1:
                issues.append(
                    self._error(
                        "DUPLICATE_COLUMN_MAPPING",
                        "A column index is mapped more than once",
                        worksheet_name,
                        column_index,
                    )
                )

        identifier_columns = tuple(
            column.column_index
            for column in mapping.mappings
            if column.semantic_label == "Identifier"
        )
        if len(identifier_columns) > 1:
            issues.append(
                self._error(
                    "DUPLICATE_IDENTIFIER",
                    "Multiple columns are mapped as Identifier",
                    worksheet_name,
                )
            )

        if objects.primary_object.object_type == "Unknown":
            issues.append(
                self._error(
                    "UNKNOWN_OBJECT",
                    "The primary enterprise object is Unknown",
                    worksheet_name,
                )
            )

        detected_objects = (
            objects.primary_object,
            *objects.related_objects,
        )
        available_labels = frozenset(
            column.semantic_label for column in mapping.mappings
        )
        for detected in detected_objects:
            for required_label in self._REQUIRED_LABELS.get(
                detected.object_type,
                (),
            ):
                if required_label not in available_labels:
                    issues.append(
                        self._error(
                            "MISSING_REQUIRED_FIELD",
                            (
                                f"{detected.object_type} requires a "
                                f"{required_label} mapping"
                            ),
                            worksheet_name,
                        )
                    )

            for column_index in detected.source_columns:
                if column_index not in schema_index_set:
                    issues.append(
                        self._error(
                            "OBJECT_SCHEMA_MISMATCH",
                            "Detected object references an absent schema column",
                            worksheet_name,
                            column_index,
                        )
                    )
                    continue
                column_mapping = mappings_by_index.get(column_index)
                if column_mapping is None:
                    issues.append(
                        self._error(
                            "MISSING_REQUIRED_MAPPING",
                            "Detected object column has no mapping",
                            worksheet_name,
                            column_index,
                        )
                    )
                elif column_mapping.semantic_label == "Unknown":
                    issues.append(
                        self._error(
                            "UNKNOWN_MANDATORY_FIELD",
                            "A mandatory object column remains Unknown",
                            worksheet_name,
                            column_index,
                        )
                    )

        for column in mapping.mappings:
            if column.semantic_label == "Unknown":
                issues.append(
                    ValidationIssue(
                        severity="WARNING",
                        code="UNKNOWN_COLUMN",
                        message="Column semantic meaning remains Unknown",
                        worksheet_name=worksheet_name,
                        column_index=column.column_index,
                    )
                )

        return tuple(issues)

    @staticmethod
    def _error(
        code: str,
        message: str,
        worksheet_name: str,
        column_index: int | None = None,
    ) -> ValidationIssue:
        return ValidationIssue(
            severity="ERROR",
            code=code,
            message=message,
            worksheet_name=worksheet_name,
            column_index=column_index,
        )


__all__ = ["ValidationEngine"]
