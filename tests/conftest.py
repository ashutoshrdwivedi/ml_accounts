"""Shared test fixtures: mock provider and mock LLM client."""

from __future__ import annotations

import json
from datetime import date

import pytest

from app.models.account import Account
from app.models.contact import Contact
from app.models.invoice import Bill, Invoice, InvoiceLine
from app.models.transaction import BankTransaction, Transaction
from app.providers.base import AccountingProvider


# ---------------------------------------------------------------------------
# Mock provider with in-memory data
# ---------------------------------------------------------------------------

class MockProvider(AccountingProvider):
    def __init__(self) -> None:
        self.accounts = [
            Account(id="acc1", name="Office Supplies", type="expense", code="5001"),
            Account(id="acc2", name="Sales Revenue", type="income", code="4001"),
            Account(id="acc3", name="Rent", type="expense", code="5002"),
            Account(id="acc4", name="Utilities", type="expense", code="5003"),
            Account(id="acc5", name="Accounts Receivable", type="asset", code="1001"),
        ]
        self.transactions = [
            Transaction(
                id="txn1", date=date(2024, 1, 15), amount=150.00,
                description="Staples - office supplies", type="debit",
            ),
            Transaction(
                id="txn2", date=date(2024, 1, 20), amount=5000.00,
                description="Client payment - Acme Corp", type="credit",
                contact_name="Acme Corp",
            ),
            Transaction(
                id="txn3", date=date(2024, 2, 1), amount=2000.00,
                description="Monthly rent payment", type="debit",
                contact_name="Landlord Inc",
            ),
            Transaction(
                id="txn4", date=date(2024, 2, 5), amount=75000.00,
                description="Suspicious large payment", type="debit",
                contact_name="Unknown Vendor",
            ),
        ]
        self.bank_transactions = [
            BankTransaction(
                id="bt1", date=date(2024, 1, 16), amount=150.00,
                description="STAPLES STORE #123", bank_account_id="bank1",
            ),
            BankTransaction(
                id="bt2", date=date(2024, 1, 21), amount=5000.00,
                description="ACH DEPOSIT ACME CORP", bank_account_id="bank1",
            ),
        ]
        self.invoices = [
            Invoice(
                id="inv1", number="INV-001", date=date(2024, 1, 10),
                due_date=date(2024, 2, 10), contact_id="c1",
                contact_name="Acme Corp", total=5000.00,
                balance_due=5000.00, status="sent",
                lines=[InvoiceLine(description="Consulting", quantity=10, rate=500, amount=5000)],
            ),
        ]
        self.bills = [
            Bill(
                id="bill1", number="BILL-001", date=date(2024, 1, 5),
                due_date=date(2024, 2, 5), contact_id="v1",
                contact_name="Landlord Inc", total=2000.00,
                balance_due=2000.00, status="open",
            ),
        ]
        self.contacts = [
            Contact(id="c1", name="Acme Corp", email="a@acme.com", type="customer"),
            Contact(id="v1", name="Landlord Inc", email="l@landlord.com", type="vendor"),
        ]

    async def list_accounts(self) -> list[Account]:
        return self.accounts

    async def get_account(self, account_id: str) -> Account:
        for a in self.accounts:
            if a.id == account_id:
                return a
        raise ValueError(f"Account {account_id} not found")

    async def list_transactions(self, start_date=None, end_date=None, **filters):
        return self.transactions

    async def update_transaction_category(self, txn_id, account_id):
        for i, t in enumerate(self.transactions):
            if t.id == txn_id:
                self.transactions[i] = t.model_copy(update={"account_id": account_id})
                return self.transactions[i]
        raise ValueError(f"Transaction {txn_id} not found")

    async def list_bank_transactions(self, bank_account_id, start_date=None, end_date=None):
        return [bt for bt in self.bank_transactions if bt.bank_account_id == bank_account_id]

    async def match_bank_transaction(self, bank_txn_id, entity_id, entity_type):
        return True

    async def list_invoices(self, start_date=None, end_date=None, status=None):
        if status:
            return [inv for inv in self.invoices if inv.status == status]
        return self.invoices

    async def list_bills(self, start_date=None, end_date=None, status=None):
        if status:
            return [b for b in self.bills if b.status == status]
        return self.bills

    async def create_invoice(self, invoice):
        invoice = invoice.model_copy(update={"id": "inv-new"})
        self.invoices.append(invoice)
        return invoice

    async def list_contacts(self, contact_type=None):
        if contact_type:
            return [c for c in self.contacts if c.type == contact_type]
        return self.contacts

    async def upload_document(self, file_bytes, filename):
        return "doc-123"


# ---------------------------------------------------------------------------
# Mock LLM client with canned responses
# ---------------------------------------------------------------------------

class MockLLMClient:
    """Mock LLM that returns deterministic JSON based on the schema requested."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def complete(self, system: str, prompt: str, model: str | None = None) -> str:
        self.calls.append({"method": "complete", "system": system, "prompt": prompt})
        return '{"result": "mock"}'

    async def complete_json(self, system, prompt, schema, model=None):
        self.calls.append({"method": "complete_json", "system": system, "prompt": prompt, "schema": schema.__name__})
        name = schema.__name__

        if name == "BatchCategoryResult":
            return schema.model_validate({
                "assignments": [
                    {"transaction_id": "txn1", "account_id": "acc1", "account_name": "Office Supplies", "confidence": 0.95},
                    {"transaction_id": "txn2", "account_id": "acc2", "account_name": "Sales Revenue", "confidence": 0.90},
                    {"transaction_id": "txn3", "account_id": "acc3", "account_name": "Rent", "confidence": 0.88},
                    {"transaction_id": "txn4", "account_id": "acc4", "account_name": "Utilities", "confidence": 0.30},
                ]
            })

        if name == "AnomalyBatchResult":
            return schema.model_validate({
                "anomalies": [
                    {
                        "transaction_id": "txn4",
                        "is_anomaly": True,
                        "severity": "high",
                        "reason": "Amount far exceeds typical range",
                        "score": 0.95,
                    }
                ]
            })

        if name == "LLMForecastResult":
            return schema.model_validate({
                "periods": [
                    {
                        "start_date": "2024-03-01",
                        "end_date": "2024-03-31",
                        "predicted_inflow": 10000.0,
                        "predicted_outflow": 7000.0,
                        "net": 3000.0,
                        "confidence_low": 2000.0,
                        "confidence_high": 4000.0,
                    }
                ],
                "summary": "Positive cash flow expected.",
            })

        if name == "MatchBatchResult":
            return schema.model_validate({
                "matches": [
                    {
                        "bank_transaction_id": "bt2",
                        "matched_entity_id": "inv1",
                        "matched_entity_type": "invoice",
                        "match_type": "exact_amount",
                        "confidence": 0.95,
                        "reasoning": "Exact amount match: $5000",
                    }
                ]
            })

        return schema.model_validate({})

    async def describe_image(self, image_bytes, prompt, model=None):
        self.calls.append({"method": "describe_image"})
        return json.dumps({
            "vendor_name": "Test Vendor",
            "invoice_number": "INV-999",
            "date": "2024-01-15",
            "due_date": "2024-02-15",
            "total": 1500.00,
            "tax": 150.00,
            "lines": [
                {"description": "Widget", "quantity": 10, "rate": 135.0, "amount": 1350.0}
            ],
            "raw_text": "Test invoice raw text",
        })


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def mock_llm():
    return MockLLMClient()
