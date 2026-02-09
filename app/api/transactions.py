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


@router.get("/categorize", response_model=list[Transaction])
async def categorize_transactions(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    transactions = await provider.list_transactions(
        start_date=start_date, end_date=end_date
    )
    uncategorized = [t for t in transactions if not t.category]
    categorizer = Categorizer(provider, llm)
    return await categorizer.categorize_transactions(uncategorized)


@router.post("/categorize/apply", response_model=list[Transaction])
async def apply_categories(
    transactions: list[Transaction],
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    categorizer = Categorizer(provider, llm)
    return await categorizer.apply_categories(transactions)


@router.get("/anomalies", response_model=list[AnomalyResult])
async def detect_anomalies(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    transactions = await provider.list_transactions(
        start_date=start_date, end_date=end_date
    )
    detector = AnomalyDetector(provider, llm)
    return await detector.detect_anomalies(transactions)
