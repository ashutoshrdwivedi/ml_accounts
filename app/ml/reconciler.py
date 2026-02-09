"""Smart bank reconciliation using LLM matching."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.models.invoice import Bill, Invoice
from app.models.reconciliation import ReconciliationMatch
from app.models.transaction import BankTransaction, Transaction

if TYPE_CHECKING:
    from app.ml.llm import LLMClient
    from app.providers.base import AccountingProvider


class MatchItem(BaseModel):
    bank_transaction_id: str
    matched_entity_id: str
    matched_entity_type: str  # invoice / bill / transaction
    match_type: str  # exact_amount / reference / description / combined
    confidence: float
    reasoning: str


class MatchBatchResult(BaseModel):
    matches: list[MatchItem]


SYSTEM_PROMPT = """\
You are a bank reconciliation specialist. Match each unmatched bank transaction
to the most likely invoice, bill, or accounting transaction.

Consider: amount (exact or close match), dates (close proximity),
reference numbers, and description similarity.

Return a JSON object with a "matches" array. Each element:
- bank_transaction_id: the bank transaction id
- matched_entity_id: the id of the matched invoice/bill/transaction
- matched_entity_type: "invoice", "bill", or "transaction"
- match_type: "exact_amount", "reference", "description", or "combined"
- confidence: 0.0-1.0
- reasoning: short explanation

Only include matches with confidence >= 0.5. Skip bank transactions with no
plausible match.
"""


class Reconciler:
    def __init__(
        self, provider: AccountingProvider, llm: LLMClient
    ) -> None:
        self._provider = provider
        self._llm = llm

    async def reconcile(
        self,
        bank_account_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[ReconciliationMatch]:
        bank_txns = await self._provider.list_bank_transactions(
            bank_account_id, start_date, end_date
        )
        unmatched = [bt for bt in bank_txns if not bt.is_matched]
        if not unmatched:
            return []

        invoices = await self._provider.list_invoices(
            start_date=start_date, end_date=end_date, status="sent"
        )
        bills = await self._provider.list_bills(
            start_date=start_date, end_date=end_date, status="open"
        )

        bank_data = [
            {
                "id": bt.id,
                "date": bt.date.isoformat(),
                "amount": bt.amount,
                "description": bt.description,
                "reference": bt.reference,
            }
            for bt in unmatched
        ]

        candidates: list[dict] = []
        for inv in invoices:
            candidates.append({
                "id": inv.id,
                "type": "invoice",
                "number": inv.number,
                "date": inv.date.isoformat() if inv.date else "",
                "amount": inv.total,
                "balance_due": inv.balance_due,
                "contact_name": inv.contact_name,
            })
        for bill in bills:
            candidates.append({
                "id": bill.id,
                "type": "bill",
                "number": bill.number,
                "date": bill.date.isoformat() if bill.date else "",
                "amount": bill.total,
                "balance_due": bill.balance_due,
                "contact_name": bill.contact_name,
            })

        prompt = (
            f"Unmatched bank transactions:\n{json.dumps(bank_data)}\n\n"
            f"Candidate invoices/bills:\n{json.dumps(candidates)}"
        )

        result = await self._llm.complete_json(
            SYSTEM_PROMPT, prompt, MatchBatchResult
        )

        bt_map = {bt.id: bt for bt in unmatched}
        inv_map = {inv.id: inv for inv in invoices}
        bill_map = {b.id: b for b in bills}

        matches: list[ReconciliationMatch] = []
        for m in result.matches:
            bt = bt_map.get(m.bank_transaction_id)
            if not bt:
                continue
            entity: Invoice | Bill | Transaction | None = None
            if m.matched_entity_type == "invoice":
                entity = inv_map.get(m.matched_entity_id)
            elif m.matched_entity_type == "bill":
                entity = bill_map.get(m.matched_entity_id)
            if entity is None:
                continue

            matches.append(
                ReconciliationMatch(
                    bank_transaction=bt,
                    matched_entity=entity,
                    match_type=m.match_type,
                    confidence=m.confidence,
                    reasoning=m.reasoning,
                )
            )

        return matches

    async def apply_matches(
        self, matches: list[ReconciliationMatch], min_confidence: float = 0.8
    ) -> int:
        applied = 0
        for m in matches:
            if m.confidence >= min_confidence:
                entity_type = type(m.matched_entity).__name__.lower()
                success = await self._provider.match_bank_transaction(
                    m.bank_transaction.id,
                    m.matched_entity.id,
                    entity_type,
                )
                if success:
                    applied += 1
        return applied
