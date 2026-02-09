from datetime import date
from typing import Literal

from pydantic import BaseModel


class Transaction(BaseModel):
    id: str
    date: date
    amount: float
    description: str
    account_id: str = ""
    account_name: str = ""
    contact_id: str = ""
    contact_name: str = ""
    reference: str = ""
    type: Literal["debit", "credit"] = "debit"
    category: str = ""
    confidence: float = 0.0


class BankTransaction(BaseModel):
    id: str
    date: date
    amount: float
    description: str
    reference: str = ""
    bank_account_id: str = ""
    is_matched: bool = False
