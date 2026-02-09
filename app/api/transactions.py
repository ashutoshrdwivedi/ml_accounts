"""Transaction endpoints: categorization and anomaly detection."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_accounting_provider, get_llm_client
from app.ml.anomaly import AnomalyDetector, AnomalyResult
from app.ml.categorizer import Categorizer
from app.ml.llm import LLMClient
from app.models.transaction import Transaction
from app.providers.base import AccountingProvider

router = APIRouter(prefix="/api/transactions", tags=["transactions"])


@router.get("/categorize", response_model=list[Transaction],
    summary="Suggest categories for transactions",
    description="Pulls uncategorized bank transactions from Zoho for the given date range, "
    "sends them to the LLM along with your chart of accounts, and returns each transaction "
    "with a suggested account and confidence score (0-1). Does NOT write anything back to Zoho.")
async def categorize_transactions(
    start_date: date = Query(..., description="Start of date range (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End of date range (YYYY-MM-DD)"),
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    transactions = await provider.list_transactions(
        start_date=start_date, end_date=end_date
    )
    uncategorized = [t for t in transactions if not t.category]
    categorizer = Categorizer(provider, llm)
    return await categorizer.categorize_transactions(uncategorized)


@router.post("/categorize/apply", response_model=list[Transaction],
    summary="Apply suggested categories to Zoho",
    description="Takes the list of categorized transactions from the /categorize endpoint "
    "and writes them back to Zoho. Only applies categories with confidence >= 0.7. "
    "Returns the list of transactions that were actually updated.")
async def apply_categories(
    transactions: list[Transaction],
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    categorizer = Categorizer(provider, llm)
    return await categorizer.apply_categories(transactions)


@router.get("/anomalies", response_model=list[AnomalyResult],
    summary="Detect anomalous transactions",
    description="Pulls transactions from Zoho for the given date range, computes statistics "
    "(average amounts per vendor, per category), and asks the LLM to flag anything unusual "
    "such as duplicate payments, amounts far from the norm, or unexpected vendors. "
    "Returns flagged transactions with severity (low/medium/high) and explanation.")
async def detect_anomalies(
    start_date: date = Query(..., description="Start of date range (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End of date range (YYYY-MM-DD)"),
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    transactions = await provider.list_transactions(
        start_date=start_date, end_date=end_date
    )
    detector = AnomalyDetector(provider, llm)
    return await detector.detect_anomalies(transactions)
