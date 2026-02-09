"""Tests for the cash flow forecaster."""

import pytest

from app.ml.forecaster import Forecaster


@pytest.mark.asyncio
async def test_forecast_cash_flow(mock_provider, mock_llm):
    forecaster = Forecaster(mock_provider, mock_llm)
    result = await forecaster.forecast_cash_flow(months_ahead=3)

    assert len(result.periods) >= 1
    period = result.periods[0]
    assert period.predicted_inflow == 10000.0
    assert period.predicted_outflow == 7000.0
    assert period.net == 3000.0
    assert result.summary != ""


@pytest.mark.asyncio
async def test_aggregate_monthly(mock_provider, mock_llm):
    forecaster = Forecaster(mock_provider, mock_llm)
    monthly = forecaster._aggregate_monthly(mock_provider.transactions)

    assert len(monthly) >= 1
    # January has both debit and credit transactions
    jan = next((m for m in monthly if m["month"] == "2024-01"), None)
    assert jan is not None
    assert jan["inflow"] > 0  # txn2 is credit
    assert jan["outflow"] > 0  # txn1 is debit
