from FINANCE import ConversationLedgerEngine


def test_conversation_ledger_parses_project_expense():
    engine = ConversationLedgerEngine()

    intent = engine.parse(
        "Bayar hotel 1500000 Project PLTU Suralaya pakai BCA MAS"
    )

    assert intent.intent == "EXPENSE"
    assert intent.amount == 1500000
    assert intent.category == "TRAVEL"
    assert intent.project == "PLTU Suralaya pakai BCA MAS"
    assert intent.payment_channel == "BCA MAS"
    assert intent.company == "PT Mitra Andalan Servisindo"


def test_conversation_ledger_parses_siluman_cash_expense():
    engine = ConversationLedgerEngine()

    intent = engine.parse(
        "Pengeluaran siluman cash 150 ribu masuk ke Project A"
    )

    assert intent.intent == "EXPENSE"
    assert intent.amount == 150000
    assert intent.category == "MISCELLANEOUS"
    assert intent.payment_channel == "CASH"


def test_conversation_ledger_creates_draft_transaction():
    engine = ConversationLedgerEngine()

    intent = engine.parse(
        "Bayar listrik 350 ribu pakai BCA"
    )

    transaction = engine.to_transaction(intent)

    assert transaction.status == "DRAFT"
    assert transaction.intent == "EXPENSE"
    assert transaction.amount == 350000
    assert transaction.category == "UTILITY"
