"""Transaction categorization using LLM."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.models.transaction import Transaction

if TYPE_CHECKING:
    from app.ml.llm import LLMClient
    from app.providers.base import AccountingProvider


class CategoryAssignment(BaseModel):
    transaction_id: str
    account_id: str
    account_name: str
    confidence: float


class BatchCategoryResult(BaseModel):
    assignments: list[CategoryAssignment]


SYSTEM_PROMPT = """\
You are an expert accountant. Given a list of transactions and a chart of accounts,
assign each transaction to the most appropriate account.

Return a JSON object with an "assignments" array. Each element must have:
- transaction_id: the transaction's id
- account_id: the matched account id
- account_name: the matched account name
- confidence: 0.0-1.0 indicating your confidence
"""

BATCH_SIZE = 30


class Categorizer:
    def __init__(
        self, provider: AccountingProvider, llm: LLMClient
    ) -> None:
        self._provider = provider
        self._llm = llm

    async def categorize_transactions(
        self, transactions: list[Transaction]
    ) -> list[Transaction]:
        if not transactions:
            return []

        accounts = await self._provider.list_accounts()
        account_list = [
            {"id": a.id, "name": a.name, "type": a.type}
            for a in accounts
            if a.is_active
        ]
        account_json = json.dumps(account_list)

        results: list[Transaction] = []
        for i in range(0, len(transactions), BATCH_SIZE):
            batch = transactions[i : i + BATCH_SIZE]
            txn_data = [
                {
                    "id": t.id,
                    "description": t.description,
                    "amount": t.amount,
                    "contact_name": t.contact_name,
                    "date": t.date.isoformat(),
                }
                for t in batch
            ]
            prompt = (
                f"Chart of Accounts:\n{account_json}\n\n"
                f"Transactions to categorize:\n{json.dumps(txn_data)}"
            )
            result = await self._llm.complete_json(
                SYSTEM_PROMPT, prompt, BatchCategoryResult
            )
            assignment_map = {a.transaction_id: a for a in result.assignments}

            for txn in batch:
                if txn.id in assignment_map:
                    a = assignment_map[txn.id]
                    txn = txn.model_copy(
                        update={
                            "account_id": a.account_id,
                            "account_name": a.account_name,
                            "category": a.account_name,
                            "confidence": a.confidence,
                        }
                    )
                results.append(txn)

        return results

    async def apply_categories(
        self, transactions: list[Transaction]
    ) -> list[Transaction]:
        applied: list[Transaction] = []
        for txn in transactions:
            if txn.account_id and txn.confidence >= 0.7:
                updated = await self._provider.update_transaction_category(
                    txn.id, txn.account_id
                )
                applied.append(updated)
        return applied
