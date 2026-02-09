from datetime import date as Date
from typing import Optional

from pydantic import BaseModel


class InvoiceLine(BaseModel):
    description: str = ""
    quantity: float = 1.0
    rate: float = 0.0
    amount: float = 0.0
    account_id: str = ""


class Invoice(BaseModel):
    id: str = ""
    number: str = ""
    date: Optional[Date] = None
    due_date: Optional[Date] = None
    contact_id: str = ""
    contact_name: str = ""
    total: float = 0.0
    balance_due: float = 0.0
    status: str = ""
    lines: list[InvoiceLine] = []


class Bill(BaseModel):
    id: str = ""
    number: str = ""
    date: Optional[Date] = None
    due_date: Optional[Date] = None
    contact_id: str = ""
    contact_name: str = ""
    total: float = 0.0
    balance_due: float = 0.0
    status: str = ""
    lines: list[InvoiceLine] = []


class ExtractedLine(BaseModel):
    description: str = ""
    quantity: float = 1.0
    rate: float = 0.0
    amount: float = 0.0


class ExtractedInvoice(BaseModel):
    vendor_name: str = ""
    invoice_number: str = ""
    date: str = ""
    due_date: str = ""
    total: float = 0.0
    tax: float = 0.0
    lines: list[ExtractedLine] = []
    raw_text: str = ""
