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


@router.get("/{bank_account_id}", response_model=list[ReconciliationMatch])
async def get_match_suggestions(
    bank_account_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
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


@router.post("/apply", response_model=ApplyMatchesResponse)
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
