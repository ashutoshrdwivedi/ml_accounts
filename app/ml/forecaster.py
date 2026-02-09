"""Cash flow forecasting using historical data + LLM."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.models.forecast import CashFlowForecast, ForecastPeriod

if TYPE_CHECKING:
    from app.ml.llm import LLMClient
    from app.providers.base import AccountingProvider


class LLMForecastPeriod(BaseModel):
    start_date: str
    end_date: str
    predicted_inflow: float
    predicted_outflow: float
    net: float
    confidence_low: float
    confidence_high: float


class LLMForecastResult(BaseModel):
    periods: list[LLMForecastPeriod]
    summary: str


SYSTEM_PROMPT = """\
You are a financial analyst. Given historical monthly cash flow data and any
known upcoming invoices/bills, produce a cash flow forecast.

Return a JSON object with:
- periods: array of monthly forecasts, each with start_date (YYYY-MM-DD),
  end_date (YYYY-MM-DD), predicted_inflow, predicted_outflow, net,
  confidence_low, confidence_high
- summary: a 2-3 sentence narrative summary of the forecast
"""


class Forecaster:
    def __init__(
        self, provider: AccountingProvider, llm: LLMClient
    ) -> None:
        self._provider = provider
        self._llm = llm

    async def forecast_cash_flow(
        self, months_ahead: int = 3
    ) -> CashFlowForecast:
        today = date.today()
        history_start = today.replace(year=today.year - 1)

        transactions = await self._provider.list_transactions(
            start_date=history_start, end_date=today
        )
        open_invoices = await self._provider.list_invoices(status="sent")
        open_bills = await self._provider.list_bills(status="open")

        monthly = self._aggregate_monthly(transactions)
        upcoming = {
            "receivables": [
                {
                    "contact": inv.contact_name,
                    "amount": inv.balance_due,
                    "due_date": inv.due_date.isoformat() if inv.due_date else "",
                }
                for inv in open_invoices
                if inv.balance_due > 0
            ],
            "payables": [
                {
                    "vendor": b.contact_name,
                    "amount": b.balance_due,
                    "due_date": b.due_date.isoformat() if b.due_date else "",
                }
                for b in open_bills
                if b.balance_due > 0
            ],
        }

        prompt = (
            f"Historical monthly cash flow (last 12 months):\n{json.dumps(monthly)}\n\n"
            f"Known upcoming items:\n{json.dumps(upcoming)}\n\n"
            f"Forecast the next {months_ahead} months starting from {today.isoformat()}."
        )

        result = await self._llm.complete_json(
            SYSTEM_PROMPT, prompt, LLMForecastResult
        )

        periods = [
            ForecastPeriod(
                start_date=date.fromisoformat(p.start_date),
                end_date=date.fromisoformat(p.end_date),
                predicted_inflow=p.predicted_inflow,
                predicted_outflow=p.predicted_outflow,
                net=p.net,
                confidence_low=p.confidence_low,
                confidence_high=p.confidence_high,
            )
            for p in result.periods
        ]

        return CashFlowForecast(
            generated_at=datetime.utcnow(),
            periods=periods,
            summary=result.summary,
        )

    def _aggregate_monthly(
        self, transactions: list
    ) -> list[dict]:
        monthly: dict[str, dict[str, float]] = defaultdict(
            lambda: {"inflow": 0.0, "outflow": 0.0}
        )
        for t in transactions:
            key = t.date.strftime("%Y-%m")
            if t.type == "credit":
                monthly[key]["inflow"] += t.amount
            else:
                monthly[key]["outflow"] += t.amount

        result = []
        for month in sorted(monthly.keys()):
            data = monthly[month]
            result.append(
                {
                    "month": month,
                    "inflow": round(data["inflow"], 2),
                    "outflow": round(data["outflow"], 2),
                    "net": round(data["inflow"] - data["outflow"], 2),
                }
            )
        return result
