from datetime import date, datetime

from pydantic import BaseModel, Field


class ForecastPeriod(BaseModel):
    start_date: date
    end_date: date
    predicted_inflow: float = 0.0
    predicted_outflow: float = 0.0
    net: float = 0.0
    confidence_low: float = 0.0
    confidence_high: float = 0.0


class CashFlowForecast(BaseModel):
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    periods: list[ForecastPeriod] = []
    summary: str = ""
