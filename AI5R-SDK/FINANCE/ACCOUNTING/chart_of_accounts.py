from dataclasses import dataclass
from enum import Enum

from FINANCE.ACCOUNTING.enterprise_accounting_architecture import (
    AccountType,
    NormalBalance,
)


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


@dataclass(frozen=True)
class ChartAccount:
    account_code: str
    account_name: str
    account_type: AccountType
    normal_balance: NormalBalance
    status: AccountStatus = AccountStatus.ACTIVE

    def validate(self) -> bool:
        return bool(
            self.account_code
            and self.account_name
            and self.account_type
            and self.normal_balance
        )


@dataclass(frozen=True)
class ChartOfAccounts:
    company_id: str
    accounts: tuple[ChartAccount, ...]

    def validate(self) -> bool:
        if not self.company_id:
            return False
        if not self.accounts:
            return False
        account_codes = [account.account_code for account in self.accounts]
        if len(account_codes) != len(set(account_codes)):
            return False
        return all(account.validate() for account in self.accounts)

    def get_account(self, account_code: str) -> ChartAccount:
        for account in self.accounts:
            if account.account_code == account_code:
                return account
        raise ValueError(f"Account not found: {account_code}")

    def accounts_by_type(self, account_type: AccountType) -> list[ChartAccount]:
        return [
            account
            for account in self.accounts
            if account.account_type == account_type
        ]


def default_chart_of_accounts(company_id: str) -> ChartOfAccounts:
    accounts = (
        ChartAccount("1000", "Cash", AccountType.ASSET, NormalBalance.DEBIT),
        ChartAccount("1100", "Accounts Receivable", AccountType.ASSET, NormalBalance.DEBIT),
        ChartAccount("1200", "Inventory", AccountType.ASSET, NormalBalance.DEBIT),
        ChartAccount("1500", "Equipment", AccountType.ASSET, NormalBalance.DEBIT),
        ChartAccount("2000", "Accounts Payable", AccountType.LIABILITY, NormalBalance.CREDIT),
        ChartAccount("2100", "Loans Payable", AccountType.LIABILITY, NormalBalance.CREDIT),
        ChartAccount("3000", "Owner Equity", AccountType.EQUITY, NormalBalance.CREDIT),
        ChartAccount("3100", "Owner Capital", AccountType.EQUITY, NormalBalance.CREDIT),
        ChartAccount("4000", "Sales Revenue", AccountType.REVENUE, NormalBalance.CREDIT),
        ChartAccount("4100", "Service Revenue", AccountType.REVENUE, NormalBalance.CREDIT),
        ChartAccount("5000", "Cost of Goods Sold", AccountType.EXPENSE, NormalBalance.DEBIT),
        ChartAccount("5100", "Marketing Expense", AccountType.EXPENSE, NormalBalance.DEBIT),
        ChartAccount("5200", "Salary Expense", AccountType.EXPENSE, NormalBalance.DEBIT),
        ChartAccount("5300", "Rent Expense", AccountType.EXPENSE, NormalBalance.DEBIT),
        ChartAccount("5400", "Utilities Expense", AccountType.EXPENSE, NormalBalance.DEBIT),
    )
    return ChartOfAccounts(company_id=company_id, accounts=accounts)
