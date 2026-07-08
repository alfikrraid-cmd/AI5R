from FINANCE.ACCOUNTING.chart_of_accounts import (
    AccountStatus,
    ChartAccount,
    ChartOfAccounts,
    default_chart_of_accounts,
)
from FINANCE.ACCOUNTING.enterprise_accounting_architecture import (
    AccountType,
    NormalBalance,
)


def test_chart_account_is_valid():
    account = ChartAccount(
        account_code="1000",
        account_name="Cash",
        account_type=AccountType.ASSET,
        normal_balance=NormalBalance.DEBIT,
    )

    assert account.validate() is True
    assert account.status == AccountStatus.ACTIVE


def test_chart_of_accounts_is_valid():
    chart = default_chart_of_accounts(company_id="PT-MAS")

    assert chart.validate() is True


def test_chart_of_accounts_requires_company_id():
    chart = ChartOfAccounts(company_id="", accounts=())

    assert chart.validate() is False


def test_chart_of_accounts_rejects_duplicate_account_code():
    account = ChartAccount(
        account_code="1000",
        account_name="Cash",
        account_type=AccountType.ASSET,
        normal_balance=NormalBalance.DEBIT,
    )
    chart = ChartOfAccounts(company_id="PT-MAS", accounts=(account, account))

    assert chart.validate() is False


def test_default_chart_contains_standard_account_types():
    chart = default_chart_of_accounts(company_id="PT-MAS")

    assert chart.accounts_by_type(AccountType.ASSET)
    assert chart.accounts_by_type(AccountType.LIABILITY)
    assert chart.accounts_by_type(AccountType.EQUITY)
    assert chart.accounts_by_type(AccountType.REVENUE)
    assert chart.accounts_by_type(AccountType.EXPENSE)


def test_get_account_by_code():
    chart = default_chart_of_accounts(company_id="PT-MAS")

    account = chart.get_account("1000")

    assert account.account_name == "Cash"
    assert account.account_type == AccountType.ASSET
    assert account.normal_balance == NormalBalance.DEBIT


def test_income_and_expense_have_correct_normal_balance():
    chart = default_chart_of_accounts(company_id="RAISHINE")

    sales = chart.get_account("4000")
    marketing = chart.get_account("5100")

    assert sales.account_type == AccountType.REVENUE
    assert sales.normal_balance == NormalBalance.CREDIT
    assert marketing.account_type == AccountType.EXPENSE
    assert marketing.normal_balance == NormalBalance.DEBIT
