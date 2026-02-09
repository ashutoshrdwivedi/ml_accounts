from abc import ABC, abstractmethod
from datetime import date

from app.models.account import Account
from app.models.contact import Contact
from app.models.invoice import Bill, Invoice
from app.models.transaction import BankTransaction, Transaction


class AccountingProvider(ABC):
    """Abstract interface for accounting backends.

    ML services depend only on this interface, never on a concrete provider.
    """

    # -- Chart of Accounts --
    @abstractmethod
    async def list_accounts(self) -> list[Account]: ...

    @abstractmethod
    async def get_account(self, account_id: str) -> Account: ...

    # -- Transactions --
    @abstractmethod
    async def list_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        **filters,
    ) -> list[Transaction]: ...

    @abstractmethod
    async def update_transaction_category(
        self, txn_id: str, account_id: str
    ) -> Transaction: ...

    # -- Bank Transactions --
    @abstractmethod
    async def list_bank_transactions(
        self,
        bank_account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[BankTransaction]: ...

    @abstractmethod
    async def match_bank_transaction(
        self, bank_txn_id: str, entity_id: str, entity_type: str
    ) -> bool: ...

    # -- Invoices & Bills --
    @abstractmethod
    async def list_invoices(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> list[Invoice]: ...

    @abstractmethod
    async def list_bills(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> list[Bill]: ...

    @abstractmethod
    async def create_invoice(self, invoice: Invoice) -> Invoice: ...

    # -- Contacts --
    @abstractmethod
    async def list_contacts(
        self, contact_type: str | None = None
    ) -> list[Contact]: ...

    # -- Documents --
    @abstractmethod
    async def upload_document(
        self, file_bytes: bytes, filename: str
    ) -> str: ...
