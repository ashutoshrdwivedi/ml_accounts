import asyncio
from typing import Any

import httpx

from app.config import Settings


class ZohoClient:
    """Async HTTP client for Zoho Books API with OAuth2 token management."""

    TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"

    def __init__(self, settings: Settings) -> None:
        self._client_id = settings.ZOHO_CLIENT_ID
        self._client_secret = settings.ZOHO_CLIENT_SECRET
        self._refresh_token = settings.ZOHO_REFRESH_TOKEN
        self._org_id = settings.ZOHO_ORG_ID
        self._base_url = settings.ZOHO_BASE_URL.rstrip("/")
        self._access_token: str | None = None
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(timeout=30.0)

    async def close(self) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        async with self._lock:
            if self._access_token is None:
                await self._refresh_access_token()
            return self._access_token  # type: ignore[return-value]

    async def _refresh_access_token(self) -> None:
        resp = await self._http.post(
            self.TOKEN_URL,
            params={
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
            },
        )
        resp.raise_for_status()
        self._access_token = resp.json()["access_token"]

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }

    async def get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._request("GET", path, params=params)

    async def post(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._request("POST", path, json=json)

    async def put(
        self, path: str, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        return await self._request("PUT", path, json=json)

    async def upload(
        self, path: str, file_bytes: bytes, filename: str
    ) -> dict[str, Any]:
        token = await self._ensure_token()
        url = f"{self._base_url}/books/v3{path}"
        headers = {"Authorization": f"Zoho-oauthtoken {token}"}
        resp = await self._http.post(
            url,
            params={"organization_id": self._org_id},
            headers=headers,
            files={"document": (filename, file_bytes)},
        )
        if resp.status_code == 401:
            await self._refresh_access_token()
            token = self._access_token  # type: ignore[assignment]
            headers = {"Authorization": f"Zoho-oauthtoken {token}"}
            resp = await self._http.post(
                url,
                params={"organization_id": self._org_id},
                headers=headers,
                files={"document": (filename, file_bytes)},
            )
        resp.raise_for_status()
        return resp.json()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        token = await self._ensure_token()
        url = f"{self._base_url}/books/v3{path}"
        merged_params = {"organization_id": self._org_id}
        if params:
            merged_params.update(params)

        resp = await self._http.request(
            method,
            url,
            params=merged_params,
            headers=self._headers(token),
            json=json,
        )
        # Retry once on 401 (expired token)
        if resp.status_code == 401:
            await self._refresh_access_token()
            token = self._access_token  # type: ignore[assignment]
            resp = await self._http.request(
                method,
                url,
                params=merged_params,
                headers=self._headers(token),
                json=json,
            )
        resp.raise_for_status()
        return resp.json()

    async def get_all_pages(
        self, path: str, key: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Paginate through all results for a list endpoint."""
        all_items: list[dict[str, Any]] = []
        page = 1
        while True:
            p = {"page": page, "per_page": 200}
            if params:
                p.update(params)
            data = await self.get(path, params=p)
            items = data.get(key, [])
            all_items.extend(items)
            page_context = data.get("page_context", {})
            if not page_context.get("has_more_page", False):
                break
            page += 1
        return all_items
