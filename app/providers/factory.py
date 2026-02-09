from app.config import Settings
from app.providers.base import AccountingProvider


def get_provider(settings: Settings) -> AccountingProvider:
    if settings.ACCOUNTING_PROVIDER == "zoho":
        from app.providers.zoho import ZohoProvider

        return ZohoProvider(settings)
    raise ValueError(f"Unknown provider: {settings.ACCOUNTING_PROVIDER}")
