"""Anomaly detection for transactions using statistical analysis + LLM."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.models.transaction import Transaction

if TYPE_CHECKING:
    from app.ml.llm import LLMClient
    from app.providers.base import AccountingProvider


class AnomalyResult(BaseModel):
    transaction: Transaction
    is_anomaly: bool
    severity: str = ""  # low / medium / high
    reason: str = ""
    score: float = 0.0


class AnomalyItem(BaseModel):
    transaction_id: str
    is_anomaly: bool
    severity: str
    reason: str
    score: float


class AnomalyBatchResult(BaseModel):
    anomalies: list[AnomalyItem]


SYSTEM_PROMPT = """\
You are a forensic accountant specializing in anomaly detection.
Analyze the transactions below given the statistical context.
Flag any that look unusual — duplicate payments, amounts far from the norm,
unexpected vendors, or timing anomalies.

Return a JSON object with an "anomalies" array. Each element:
- transaction_id: the id
- is_anomaly: true/false
- severity: "low", "medium", or "high"
- reason: short explanation
- score: 0.0-1.0 anomaly score
"""


class AnomalyDetector:
    def __init__(
        self, provider: AccountingProvider, llm: LLMClient
    ) -> None:
        self._provider = provider
        self._llm = llm

    async def detect_anomalies(
        self, transactions: list[Transaction]
    ) -> list[AnomalyResult]:
        if not transactions:
            return []

        stats = self._compute_stats(transactions)
        txn_data = [
            {
                "id": t.id,
                "date": t.date.isoformat(),
                "amount": t.amount,
                "description": t.description,
                "account_name": t.account_name,
                "contact_name": t.contact_name,
                "type": t.type,
            }
            for t in transactions
        ]

        prompt = (
            f"Statistical context:\n{json.dumps(stats)}\n\n"
            f"Transactions:\n{json.dumps(txn_data)}"
        )
        result = await self._llm.complete_json(
            SYSTEM_PROMPT, prompt, AnomalyBatchResult
        )

        anomaly_map = {a.transaction_id: a for a in result.anomalies}
        txn_map = {t.id: t for t in transactions}

        results: list[AnomalyResult] = []
        for item in result.anomalies:
            if item.transaction_id in txn_map:
                results.append(
                    AnomalyResult(
                        transaction=txn_map[item.transaction_id],
                        is_anomaly=item.is_anomaly,
                        severity=item.severity,
                        reason=item.reason,
                        score=item.score,
                    )
                )
        return results

    def _compute_stats(
        self, transactions: list[Transaction]
    ) -> dict:
        by_account: dict[str, list[float]] = defaultdict(list)
        by_contact: dict[str, list[float]] = defaultdict(list)

        for t in transactions:
            if t.account_name:
                by_account[t.account_name].append(t.amount)
            if t.contact_name:
                by_contact[t.contact_name].append(t.amount)

        def summarize(groups: dict[str, list[float]]) -> dict:
            out = {}
            for name, amounts in groups.items():
                n = len(amounts)
                mean = sum(amounts) / n
                variance = sum((a - mean) ** 2 for a in amounts) / n if n > 1 else 0
                std = variance**0.5
                out[name] = {
                    "count": n,
                    "mean": round(mean, 2),
                    "std": round(std, 2),
                    "min": round(min(amounts), 2),
                    "max": round(max(amounts), 2),
                }
            return out

        return {
            "by_account": summarize(by_account),
            "by_contact": summarize(by_contact),
            "total_transactions": len(transactions),
        }
