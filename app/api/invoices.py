"""Invoice endpoints: extraction and creation from extracted data."""

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import get_accounting_provider, get_llm_client
from app.ml.extractor import Extractor
from app.ml.llm import LLMClient
from app.models.invoice import ExtractedInvoice, Invoice, InvoiceLine
from app.providers.base import AccountingProvider

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


@router.post("/extract", response_model=ExtractedInvoice,
    summary="Extract data from an invoice image or PDF",
    description="Upload an invoice file (image or PDF). The LLM vision API reads it and "
    "extracts structured data: vendor name, invoice number, dates, line items, totals, and tax. "
    "Returns the extracted data for review. Does NOT create anything in Zoho yet.")
async def extract_invoice(
    file: UploadFile,
    provider: AccountingProvider = Depends(get_accounting_provider),
    llm: LLMClient = Depends(get_llm_client),
):
    file_bytes = await file.read()
    extractor = Extractor(provider, llm)
    return await extractor.extract_invoice(file_bytes, file.filename or "upload")


@router.post("/extract/create", response_model=Invoice,
    summary="Create a Zoho invoice from extracted data",
    description="Takes the extracted invoice data from the /extract endpoint and creates "
    "an actual invoice in Zoho Books. Automatically matches the vendor name to an existing "
    "Zoho contact if one exists. Pass the response from /extract directly as the request body.")
async def create_from_extracted(
    extracted: ExtractedInvoice,
    provider: AccountingProvider = Depends(get_accounting_provider),
):
    contacts = await provider.list_contacts()
    contact_id = ""
    for c in contacts:
        if c.name.lower() == extracted.vendor_name.lower():
            contact_id = c.id
            break

    lines = [
        InvoiceLine(
            description=line.description,
            quantity=line.quantity,
            rate=line.rate,
            amount=line.amount,
        )
        for line in extracted.lines
    ]

    invoice = Invoice(
        contact_id=contact_id,
        contact_name=extracted.vendor_name,
        total=extracted.total,
        lines=lines,
    )
    return await provider.create_invoice(invoice)
