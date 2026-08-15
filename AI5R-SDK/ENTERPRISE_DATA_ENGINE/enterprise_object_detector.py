from .column_mapping import DatasetColumnMapping
from .dataset_schema import DatasetSchema
from .detected_enterprise_object import (
    DetectedEnterpriseObject,
    DetectedEnterpriseObjects,
)
from .document_classification import DocumentClassification


class EnterpriseObjectDetector:
    """Produce immutable object descriptors without creating domain objects."""

    __slots__ = ()

    _DOCUMENT_OBJECTS = {
        "Unknown": ("Unknown", ()),
        "Bank Statement": ("BankTransaction", ()),
        "Journal": ("Journal", ()),
        "General Ledger": ("GeneralLedger", ()),
        "Trial Balance": ("TrialBalance", ()),
        "Sales Invoice": ("Invoice", ("Customer",)),
        "Purchase Invoice": ("Invoice", ("Vendor",)),
        "Customer List": ("Customer", ()),
        "Vendor List": ("Vendor", ()),
        "Inventory": ("InventoryItem", ()),
        "Payroll": ("Payroll", ("Employee",)),
        "Equipment": ("Equipment", ()),
    }

    _OBJECT_LABELS = {
        "Unknown": (),
        "BankTransaction": ("Date", "Description", "Amount", "Identifier"),
        "Journal": ("Date", "Description", "Amount", "Code", "Identifier"),
        "GeneralLedger": ("Date", "Description", "Amount", "Code", "Identifier"),
        "TrialBalance": ("Amount", "Code", "Name", "Identifier"),
        "Invoice": ("Date", "Description", "Amount", "Quantity", "Code", "Identifier"),
        "Customer": ("Name", "Address", "Phone", "Email", "Code", "Identifier"),
        "Vendor": ("Name", "Address", "Phone", "Email", "Code", "Identifier"),
        "InventoryItem": ("Code", "Name", "Description", "Quantity", "Amount"),
        "Equipment": ("Code", "Identifier", "Name", "Description"),
        "Employee": ("Identifier", "Code", "Name", "Address", "Phone", "Email"),
        "Payroll": ("Date", "Description", "Amount", "Quantity", "Identifier"),
    }

    def detect(self, classification, mapping, schema):
        if isinstance(classification, DocumentClassification):
            return self._detect_one(classification, mapping, schema)
        return tuple(
            self._detect_one(item_classification, item_mapping, item_schema)
            for item_classification, item_mapping, item_schema in zip(
                classification,
                mapping,
                schema,
            )
        )

    @staticmethod
    def primary_object(
        objects: DetectedEnterpriseObjects,
    ) -> DetectedEnterpriseObject:
        return objects.primary_object

    @staticmethod
    def related_objects(
        objects: DetectedEnterpriseObjects,
    ) -> tuple[DetectedEnterpriseObject, ...]:
        return objects.related_objects

    @staticmethod
    def confidence(
        objects: DetectedEnterpriseObject | DetectedEnterpriseObjects,
    ) -> float:
        if isinstance(objects, DetectedEnterpriseObjects):
            return objects.primary_object.confidence
        return objects.confidence

    def _detect_one(
        self,
        classification: DocumentClassification,
        mapping: DatasetColumnMapping,
        schema: DatasetSchema,
    ) -> DetectedEnterpriseObjects:
        primary_type, related_types = self._DOCUMENT_OBJECTS.get(
            classification.primary_type,
            ("Unknown", ()),
        )
        primary = self._descriptor(
            primary_type,
            "Primary",
            classification.confidence,
            classification.primary_type,
            mapping,
            schema,
        )
        related = tuple(
            self._descriptor(
                object_type,
                "Related",
                round(classification.confidence * 0.9, 4),
                classification.primary_type,
                mapping,
                schema,
            )
            for object_type in related_types
        )
        return DetectedEnterpriseObjects(
            worksheet_name=schema.worksheet_name,
            document_type=classification.primary_type,
            primary_object=primary,
            related_objects=related,
        )

    def _descriptor(
        self,
        object_type: str,
        role: str,
        confidence: float,
        document_type: str,
        mapping: DatasetColumnMapping,
        schema: DatasetSchema,
    ) -> DetectedEnterpriseObject:
        labels = frozenset(self._OBJECT_LABELS[object_type])
        schema_columns = frozenset(
            column.column_index for column in schema.columns
        )
        source_columns = tuple(
            item.column_index
            for item in mapping.mappings
            if item.column_index in schema_columns
            and item.semantic_label in labels
        )
        return DetectedEnterpriseObject(
            object_type=object_type,
            role=role,
            confidence=confidence,
            source_columns=source_columns,
            document_type=document_type,
        )


__all__ = ["EnterpriseObjectDetector"]
