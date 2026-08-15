import re
import unicodedata

from .column_mapping import DatasetColumnMapping
from .dataset_schema import DatasetSchema
from .document_classification import (
    DocumentCandidate,
    DocumentClassification,
)


class DocumentClassifier:
    """Classify document structure with deterministic, explicit signatures."""

    __slots__ = ()

    _RULES = (
        (
            "Bank Statement",
            (("bank", "bank statement", "rekening", "mutasi rekening"),),
            (
                ("label", "Date"),
                ("label", "Description"),
                ("label", "Amount"),
                ("keyword", "balance", "saldo", "transaction", "transaksi"),
            ),
        ),
        (
            "Journal",
            (
                ("journal", "jurnal", "debit"),
                ("journal", "jurnal", "credit", "kredit"),
            ),
            (
                ("label", "Date"),
                ("label", "Description"),
                ("label", "Amount"),
            ),
        ),
        (
            "General Ledger",
            (("general ledger", "buku besar"),),
            (
                ("keyword", "account", "akun"),
                ("keyword", "debit"),
                ("keyword", "credit", "kredit"),
                ("keyword", "balance", "saldo"),
            ),
        ),
        (
            "Trial Balance",
            (("trial balance", "neraca saldo"),),
            (
                ("keyword", "account", "akun"),
                ("keyword", "debit"),
                ("keyword", "credit", "kredit"),
            ),
        ),
        (
            "Sales Invoice",
            (("sales invoice", "faktur penjualan", "invoice", "faktur"),),
            (
                ("keyword", "sales", "penjualan", "customer", "pelanggan"),
                ("label", "Date"),
                ("label", "Amount"),
                ("label", "Description"),
            ),
        ),
        (
            "Purchase Invoice",
            (("purchase invoice", "faktur pembelian", "invoice", "faktur"),),
            (
                ("keyword", "purchase", "pembelian", "vendor", "supplier", "pemasok"),
                ("label", "Date"),
                ("label", "Amount"),
                ("label", "Description"),
            ),
        ),
        (
            "Customer List",
            (("customer", "customers", "pelanggan"),),
            (
                ("label", "Name"),
                ("label", "Address", "Phone", "Email"),
                ("label", "Code", "Identifier"),
            ),
        ),
        (
            "Vendor List",
            (("vendor", "vendors", "supplier", "pemasok"),),
            (
                ("label", "Name"),
                ("label", "Address", "Phone", "Email"),
                ("label", "Code", "Identifier"),
            ),
        ),
        (
            "Inventory",
            (("inventory", "stock", "stok", "item", "product", "material", "barang"),),
            (
                ("label", "Code"),
                ("label", "Name"),
                ("label", "Quantity"),
            ),
        ),
        (
            "Payroll",
            (("payroll", "salary", "gaji", "upah"),),
            (
                ("keyword", "employee", "karyawan", "pegawai"),
                ("label", "Name"),
                ("label", "Amount"),
            ),
        ),
        (
            "Equipment",
            (("equipment", "asset", "machine", "mesin", "peralatan"),),
            (
                ("label", "Code", "Identifier"),
                ("label", "Name"),
                ("label", "Description"),
            ),
        ),
    )

    def classify(
        self,
        schema: DatasetSchema,
        mapping: DatasetColumnMapping,
    ) -> DocumentClassification:
        header_text = " ".join(
            self._normalize(column.header) for column in schema.columns
        )
        labels = frozenset(item.semantic_label for item in mapping.mappings)
        candidates = []

        for order, (document_type, required, optional) in enumerate(self._RULES):
            required_matches = tuple(
                self._keyword_match(header_text, group) for group in required
            )
            if not all(required_matches):
                continue

            optional_matches = tuple(
                self._signal_match(header_text, labels, signal)
                for signal in optional
            )
            matches = required_matches + optional_matches
            confidence = round(sum(matches) / len(matches), 4)
            matched_signals = tuple(
                f"signal-{index}"
                for index, matched in enumerate(matches)
                if matched
            )
            candidates.append(
                (
                    order,
                    DocumentCandidate(
                        document_type=document_type,
                        confidence=confidence,
                        matched_signals=matched_signals,
                    ),
                )
            )

        if not candidates:
            unknown = DocumentCandidate("Unknown", 0.0)
            return DocumentClassification(
                worksheet_name=schema.worksheet_name,
                primary_type="Unknown",
                confidence=0.0,
                candidates=(unknown,),
            )

        ordered = tuple(
            candidate
            for _, candidate in sorted(
                candidates,
                key=lambda item: (-item[1].confidence, item[0]),
            )
        )
        return DocumentClassification(
            worksheet_name=schema.worksheet_name,
            primary_type=ordered[0].document_type,
            confidence=ordered[0].confidence,
            candidates=ordered,
        )

    @staticmethod
    def confidence(classification: DocumentClassification) -> float:
        return classification.confidence

    @staticmethod
    def candidate_types(
        classification: DocumentClassification,
    ) -> tuple[str, ...]:
        return tuple(
            candidate.document_type for candidate in classification.candidates
        )

    @staticmethod
    def primary_type(classification: DocumentClassification) -> str:
        return classification.primary_type

    @classmethod
    def _signal_match(cls, header_text, labels, signal) -> bool:
        signal_type, *values = signal
        if signal_type == "label":
            return any(value in labels for value in values)
        return cls._keyword_match(header_text, values)

    @classmethod
    def _keyword_match(cls, header_text, keywords) -> bool:
        padded = f" {header_text} "
        return any(
            f" {cls._normalize(keyword)} " in padded for keyword in keywords
        )

    @staticmethod
    def _normalize(value) -> str:
        if not isinstance(value, str):
            return ""
        decomposed = unicodedata.normalize("NFKD", value)
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


__all__ = ["DocumentClassifier"]
