"""Tests for the invoice extractor."""

import pytest

from app.ml.extractor import Extractor


@pytest.mark.asyncio
async def test_extract_invoice(mock_provider, mock_llm):
    extractor = Extractor(mock_provider, mock_llm)
    result = await extractor.extract_invoice(b"fake-image-bytes", "invoice.png")

    assert result.vendor_name == "Test Vendor"
    assert result.invoice_number == "INV-999"
    assert result.total == 1500.00
    assert result.tax == 150.00
    assert len(result.lines) == 1
    assert result.lines[0].description == "Widget"
    assert result.lines[0].quantity == 10
