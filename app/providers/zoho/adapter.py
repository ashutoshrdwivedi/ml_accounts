from datetime import date

from app.config import Settings
from app.models.account import Account
from app.models.contact import Contact
from app.models.invoice import Bill, Invoice
from app.models.transaction import BankTransaction, Transaction
from app.providers.base import AccountingProvider

from . import mappers
from .client import ZohoClient


class ZohoProvider(AccountingProvider):
    def __init__(self, settings: Settings) -> None:
        self._client = ZohoClient(settings)

    async def close(self) -> None:
        await self._client.close()

    # -- Chart of Accounts --

    async def list_accounts(self) -> list[Account]:
        items = await self._client.get_all_pages(
            "/chartofaccounts", "chartofaccounts"
        )
        return [mappers.zoho_account_to_model(a) for a in items]

    async def get_account(self, account_id: str) -> Account:
        data = await self._client.get(f"/chartofaccounts/{account_id}")
        return mappers.zoho_account_to_model(data["account"])

    # -- Transactions (backed by Zoho bank transactions) --

    async def list_transactions(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        **filters,
    ) -> list[Transaction]:
        params: dict = {}
        if start_date:
            params["date_start"] = start_date.isoformat()
        if end_date:
            params["date_end"] = end_date.isoformat()
        params.update(filters)
        items = await self._client.get_all_pages(
            "/banktransactions", "banktransactions", params=params
        )
        return [mappers.zoho_transaction_to_model(t) for t in items]

    async def update_transaction_category(
        self, txn_id: str, account_id: str
    ) -> Transaction:
        data = await self._client.post(
            f"/banktransactions/uncategorized/{txn_id}/categorize",
            json={"account_id": account_id},
        )
        return mappers.zoho_transaction_to_model(data.get("transaction", data))

    # -- Bank Transactions --

    async def list_bank_transactions(
        self,
        bank_account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[BankTransaction]:
        params: dict = {"account_id": bank_account_id}
        if start_date:
            params["date_start"] = start_date.isoformat()
        if end_date:
            params["date_end"] = end_date.isoformat()
        items = await self._client.get_all_pages(
            "/banktransactions", "banktransactions", params=params
        )
        return [mappers.zoho_bank_transaction_to_model(bt) for bt in items]

    async def match_bank_transaction(
        self, bank_txn_id: str, entity_id: str, entity_type: str
    ) -> bool:
        await self._client.post(
            f"/banktransactions/uncategorized/{bank_txn_id}/match",
            json={
                "transactions_to_be_matched": [
                    {"transaction_id": entity_id, "transaction_type": entity_type}
                ]
            },
        )
        return True

    # -- Invoices --

    async def list_invoices(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> list[Invoice]:
        params: dict = {}
        if start_date:
            params["date_start"] = start_date.isoformat()
        if end_date:
            params["date_end"] = end_date.isoformat()
        if status:
            params["status"] = status
        items = await self._client.get_all_pages(
            "/invoices", "invoices", params=params
        )
        return [mappers.zoho_invoice_to_model(inv) for inv in items]

    async def list_bills(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        status: str | None = None,
    ) -> list[Bill]:
        params: dict = {}
        if start_date:
            params["date_start"] = start_date.isoformat()
        if end_date:
            params["date_end"] = end_date.isoformat()
        if status:
            params["status"] = status
        items = await self._client.get_all_pages(
            "/bills", "bills", params=params
        )
        return [mappers.zoho_bill_to_model(b) for b in items]

    async def create_invoice(self, invoice: Invoice) -> Invoice:
        payload = mappers.invoice_to_zoho_json(invoice)
        data = await self._client.post("/invoices", json=payload)
        return mappers.zoho_invoice_to_model(data["invoice"])

    # -- Contacts --

    async def list_contacts(
        self, contact_type: str | None = None
    ) -> list[Contact]:
        params: dict = {}
        if contact_type:
            params["contact_type"] = contact_type
        items = await self._client.get_all_pages(
            "/contacts", "contacts", params=params
        )
        return [mappers.zoho_contact_to_model(c) for c in items]

    # -- Documents --

    async def upload_document(
        self, file_bytes: bytes, filename: str
    ) -> str:
        data = await self._client.upload(
            "/documents", file_bytes, filename
        )
        return str(data.get("document", {}).get("document_id", ""))
