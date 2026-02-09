"""Pure mapping functions: Zoho JSON <-> canonical models."""

from datetime import date
from typing import Any

from app.models.account import Account
from app.models.contact import Contact
from app.models.invoice import Bill, Invoice, InvoiceLine
from app.models.transaction import BankTransaction, Transaction

# -- Account --

ZOHO_ACCOUNT_TYPE_MAP: dict[str, str] = {
    "asset": "asset",
    "liability": "liability",
    "equity": "equity",
    "income": "income",
    "expense": "expense",
    "other_asset": "asset",
    "other_liability": "liability",
    "other_current_asset": "asset",
    "other_current_liability": "liability",
    "fixed_asset": "asset",
    "long_term_liability": "liability",
    "cost_of_goods_sold": "expense",
    "other_expense": "expense",
    "other_income": "income",
    "accounts_receivable": "asset",
    "accounts_payable": "liability",
    "bank": "asset",
    "cash": "asset",
    "stock": "equity",
}


def zoho_account_to_model(data: dict[str, Any]) -> Account:
    raw_type = data.get("account_type", "expense").lower().replace(" ", "_")
    return Account(
        id=str(data["account_id"]),
        name=data.get("account_name", ""),
        type=ZOHO_ACCOUNT_TYPE_MAP.get(raw_type, "expense"),
        code=data.get("account_code", ""),
        parent_id=str(data["parent_account_id"]) if data.get("parent_account_id") else None,
        is_active=data.get("is_active", True),
    )


# -- Transaction --

def _parse_date(val: str | None) -> date:
    if not val:
        return date.today()
    return date.fromisoformat(val)


def zoho_transaction_to_model(data: dict[str, Any]) -> Transaction:
    return Transaction(
        id=str(data.get("transaction_id", data.get("journal_id", ""))),
        date=_parse_date(data.get("date")),
        amount=float(data.get("amount", data.get("debit_or_credit", 0))),
        description=data.get("description", data.get("narration", "")),
        account_id=str(data.get("account_id", "")),
        account_name=data.get("account_name", ""),
        contact_id=str(data.get("contact_id", "")),
        contact_name=data.get("contact_name", ""),
        reference=data.get("reference_number", ""),
        type="debit" if float(data.get("debit_amount", data.get("amount", 0))) > 0 else "credit",
    )


# -- Bank Transaction --

def zoho_bank_transaction_to_model(data: dict[str, Any]) -> BankTransaction:
    return BankTransaction(
        id=str(data.get("transaction_id", data.get("statement_line_id", ""))),
        date=_parse_date(data.get("date")),
        amount=float(data.get("amount", 0)),
        description=data.get("description", data.get("payee", "")),
        reference=data.get("reference_number", ""),
        bank_account_id=str(data.get("account_id", "")),
        is_matched=data.get("is_matched", False),
    )


# -- Invoice --

def _zoho_line_to_model(data: dict[str, Any]) -> InvoiceLine:
    return InvoiceLine(
        description=data.get("description", data.get("name", "")),
        quantity=float(data.get("quantity", 1)),
        rate=float(data.get("rate", 0)),
        amount=float(data.get("item_total", data.get("amount", 0))),
        account_id=str(data.get("account_id", "")),
    )


def zoho_invoice_to_model(data: dict[str, Any]) -> Invoice:
    lines = [_zoho_line_to_model(li) for li in data.get("line_items", [])]
    return Invoice(
        id=str(data.get("invoice_id", "")),
        number=data.get("invoice_number", ""),
        date=_parse_date(data.get("date")),
        due_date=_parse_date(data.get("due_date")) if data.get("due_date") else None,
        contact_id=str(data.get("customer_id", "")),
        contact_name=data.get("customer_name", ""),
        total=float(data.get("total", 0)),
        balance_due=float(data.get("balance", 0)),
        status=data.get("status", ""),
        lines=lines,
    )


def zoho_bill_to_model(data: dict[str, Any]) -> Bill:
    lines = [_zoho_line_to_model(li) for li in data.get("line_items", [])]
    return Bill(
        id=str(data.get("bill_id", "")),
        number=data.get("bill_number", ""),
        date=_parse_date(data.get("date")),
        due_date=_parse_date(data.get("due_date")) if data.get("due_date") else None,
        contact_id=str(data.get("vendor_id", "")),
        contact_name=data.get("vendor_name", ""),
        total=float(data.get("total", 0)),
        balance_due=float(data.get("balance", 0)),
        status=data.get("status", ""),
        lines=lines,
    )


# -- Contact --

def zoho_contact_to_model(data: dict[str, Any]) -> Contact:
    ct = data.get("contact_type", "customer")
    if ct not in ("customer", "vendor", "both"):
        ct = "customer"
    return Contact(
        id=str(data.get("contact_id", "")),
        name=data.get("contact_name", ""),
        email=data.get("email", ""),
        type=ct,
    )


# -- Model -> Zoho JSON (for creates) --

def invoice_to_zoho_json(invoice: Invoice) -> dict[str, Any]:
    lines = []
    for li in invoice.lines:
        lines.append({
            "description": li.description,
            "quantity": li.quantity,
            "rate": li.rate,
            "account_id": li.account_id,
        })
    payload: dict[str, Any] = {
        "customer_id": invoice.contact_id,
        "line_items": lines,
    }
    if invoice.date:
        payload["date"] = invoice.date.isoformat()
    if invoice.due_date:
        payload["due_date"] = invoice.due_date.isoformat()
    return payload
