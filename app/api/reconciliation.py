"""Bank reconciliation endpoints."""

from datetime import date

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.api.deps import get_accounting_provider, get_llm_client
from app.ml.llm import LLMClient
from app.ml.reconciler import Reconciler
from app.models.reconciliation import ReconciliationMatch
from app.providers.base import AccountingProvider

router = APIRouter(prefix="/api/reconciliation", tags=["reconciliation"])


@router.get("/{bank_account_id}", response_model=list[ReconciliationMatch],
    summary="Get bank reconciliation suggestions",
    description="Pulls unmatched bank transactions and open invoices/bills from Zoho for the "
    "given bank account and date range. The LLM matches them by amount, date, reference number, "
    "and description similarity. Returns suggested matches with confidence scores and reasoning. "
    "Does NOT apply any matches yet. Find your bank_account_id in Zoho Books under Banking.")
async def get_match_suggestions(
    bank_account_id: str,
    start_date: date = Query(..., description="Start of date range (YYYY-MM-DD)"),
    end_date: date = Query(..., description="End of date range (YYYY-MM-DD)"),
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    reconciler = Reconciler(provider, llm)
    return await reconciler.reconcile(bank_account_id, start_date, end_date)


class ApplyMatchesRequest(BaseModel):
    matches: list[ReconciliationMatch]
    min_confidence: float = 0.8


class ApplyMatchesResponse(BaseModel):
    applied_count: int


@router.post("/apply", response_model=ApplyMatchesResponse,
    summary="Apply reconciliation matches to Zoho",
    description="Takes the match suggestions from the GET endpoint and applies them in Zoho. "
    "Only matches with confidence >= min_confidence (default 0.8) are applied. "
    "Returns the number of matches that were successfully applied.")
async def apply_matches(
    request: ApplyMatchesRequest,
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    reconciler = Reconciler(provider, llm)
    count = await reconciler.apply_matches(
        request.matches, request.min_confidence
    )
    return ApplyMatchesResponse(applied_count=count)
