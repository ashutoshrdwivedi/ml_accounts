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
    description="ML layer for accounting software",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transactions.router)
app.include_router(invoices.router)
app.include_router(forecasts.router)
app.include_router(reconciliation.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
