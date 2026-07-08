from __future__ import annotations

import re

from .finance_intent import FinanceIntent
from .finance_transaction import FinanceTransaction


class ConversationLedgerEngine:
    def parse(self, text: str) -> FinanceIntent:
        raw = text.strip()

        if not raw:
            raise ValueError("text is required")

        lowered = raw.lower()
        amount = self._extract_amount(lowered)

        intent = "EXPENSE"

        income_words = [
            "terima",
            "diterima",
            "uang masuk",
            "payment received",
            "pembayaran diterima",
        ]

        if any(word in lowered for word in income_words):
            intent = "INCOME"

        if any(word in lowered for word in ["transfer", "pindah dana"]):
            intent = "TRANSFER"

        category = self._detect_category(lowered)
        payment_channel = self._detect_payment_channel(raw)
        project = self._detect_project(raw)
        company = self._detect_company(raw)

        return FinanceIntent(
            intent=intent,
            amount=amount,
            category=category,
            payment_channel=payment_channel,
            company=company,
            project=project,
            raw_text=raw,
            confidence=0.85,
        )

    def to_transaction(
        self,
        finance_intent: FinanceIntent,
        transaction_id: str = "FIN-TXN-000001",
    ) -> FinanceTransaction:
        return FinanceTransaction(
            transaction_id=transaction_id,
            intent=finance_intent.intent,
            amount=finance_intent.amount,
            category=finance_intent.category,
            company=finance_intent.company,
            project=finance_intent.project,
            payment_channel=finance_intent.payment_channel,
            status="DRAFT",
        )

    def _extract_amount(self, text: str) -> int:
        normalized = text.replace(".", "").replace(",", "")

        match = re.search(r"(\d+)\s*(juta|jt|ribu|rb|k)?", normalized)

        if not match:
            raise ValueError("amount is required")

        amount = int(match.group(1))
        unit = match.group(2)

        if unit in ["juta", "jt"]:
            amount *= 1_000_000

        if unit in ["ribu", "rb", "k"]:
            amount *= 1_000

        return amount

    def _detect_category(self, text: str) -> str:
        if "hotel" in text or "penginapan" in text:
            return "TRAVEL"

        if "siluman" in text:
            return "MISCELLANEOUS"

        if "listrik" in text or "air" in text:
            return "UTILITY"

        if "bahan" in text or "material" in text:
            return "RAW_MATERIAL"

        return "GENERAL_EXPENSE"

    def _detect_payment_channel(self, text: str) -> str | None:
        upper = text.upper()

        if "BCA MAS" in upper:
            return "BCA MAS"

        if "BCA" in upper:
            return "BCA"

        if "CASH" in upper or "TUNAI" in upper:
            return "CASH"

        if "QRIS" in upper:
            return "QRIS"

        return None

    def _detect_project(self, text: str) -> str | None:
        match = re.search(r"(project|proyek)\s+([A-Za-z0-9 _-]+)", text, re.IGNORECASE)

        if match:
            return match.group(2).strip()

        return None

    def _detect_company(self, text: str) -> str | None:
        upper = text.upper()

        if "MAS" in upper or "MITRA ANDALAN" in upper:
            return "PT Mitra Andalan Servisindo"

        if "RTM" in upper or "RAZZAN" in upper:
            return "CV Razzan Teknik Mandiri"

        return None
