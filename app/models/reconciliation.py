from pydantic import BaseModel

from .invoice import Bill, Invoice
from .transaction import BankTransaction, Transaction


class ReconciliationMatch(BaseModel):
    bank_transaction: BankTransaction
    matched_entity: Invoice | Bill | Transaction
    match_type: str = ""
    confidence: float = 0.0
    reasoning: str = ""
