"""Invoice data extraction from images/PDFs using LLM vision."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from app.models.invoice import ExtractedInvoice

if TYPE_CHECKING:
    from app.ml.llm import LLMClient
    from app.providers.base import AccountingProvider


EXTRACTION_PROMPT = """\
Extract all invoice data from this image. Return a JSON object with:
- vendor_name: the vendor/supplier name
- invoice_number: the invoice number
- date: invoice date (YYYY-MM-DD)
- due_date: due date (YYYY-MM-DD) if visible
- total: total amount as a number
- tax: tax amount as a number (0 if not shown)
- lines: array of line items, each with description, quantity, rate, amount
- raw_text: any other relevant text from the invoice

Be precise with numbers. If a field is not visible, use empty string or 0.
"""


class Extractor:
    def __init__(
        self, provider: AccountingProvider, llm: LLMClient
    ) -> None:
        self._provider = provider
        self._llm = llm

    async def extract_invoice(
        self, file_bytes: bytes, filename: str
    ) -> ExtractedInvoice:
        raw = await self._llm.describe_image(file_bytes, EXTRACTION_PROMPT)
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
        return ExtractedInvoice.model_validate_json(text)
