"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import forecasts, invoices, reconciliation, transactions
from app.api.deps import get_accounting_provider


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm up the provider (triggers token refresh for Zoho)
    provider = get_accounting_provider()
    yield
    # Shutdown: close provider connections if applicable
    if hasattr(provider, "close"):
        await provider.close()


app = FastAPI(
    title="ML Accounts",
    description=(
        "ML layer for accounting software. Connects to Zoho Books and uses LLMs to automate:\n\n"
        "- **Transaction categorization** - auto-assign chart of accounts entries\n"
        "- **Anomaly detection** - flag suspicious or unusual transactions\n"
        "- **Cash flow forecasting** - predict future inflows and outflows\n"
        "- **Invoice extraction** - read invoice PDFs/images into structured data\n"
        "- **Bank reconciliation** - match bank transactions to invoices and bills\n\n"
        "All GET endpoints are read-only suggestions. POST /apply endpoints write changes back to Zoho."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transactions.router)
app.include_router(invoices.router)
app.include_router(forecasts.router)
app.include_router(reconciliation.router)


@app.get("/health", summary="Health check", description="Returns ok if the service is running.")
async def health_check():
    return {"status": "ok"}
