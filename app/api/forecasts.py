"""Cash flow forecast endpoints."""

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_accounting_provider, get_llm_client
from app.ml.forecaster import Forecaster
from app.ml.llm import LLMClient
from app.models.forecast import CashFlowForecast
from app.providers.base import AccountingProvider

router = APIRouter(prefix="/api/forecasts", tags=["forecasts"])


@router.get("/cashflow", response_model=CashFlowForecast)
async def get_cash_flow_forecast(
    months: int = Query(default=3, ge=1, le=12),
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    forecaster = Forecaster(provider, llm)
    return await forecaster.forecast_cash_flow(months_ahead=months)
