# ML Accounts

ML layer for accounting software. Adds transaction categorization, anomaly detection, cash flow forecasting, invoice extraction, and bank reconciliation on top of your accounting backend.

Phase 1 integrates with Zoho Books. The architecture is provider-agnostic — swap Zoho for any backend by implementing a single abstract class.

## Setup

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env with your credentials
```

### Required environment variables

| Variable | Description |
|----------|-------------|
| `ACCOUNTING_PROVIDER` | `zoho` (default) |
| `ZOHO_CLIENT_ID` | Zoho OAuth2 client ID |
| `ZOHO_CLIENT_SECRET` | Zoho OAuth2 client secret |
| `ZOHO_REFRESH_TOKEN` | Zoho OAuth2 refresh token |
| `ZOHO_ORG_ID` | Zoho Books organization ID |
| `LLM_PROVIDER` | `openai` or `anthropic` |
| `OPENAI_API_KEY` | OpenAI API key (if using OpenAI) |
| `ANTHROPIC_API_KEY` | Anthropic API key (if using Anthropic) |
| `LLM_MODEL` | Model name, e.g. `gpt-4o` or `claude-sonnet-4-20250514` |

## Running

```bash
uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

## API endpoints

### Transactions

**Categorize transactions** — assigns each transaction to a chart-of-accounts entry using the LLM:

```
GET /api/transactions/categorize?start_date=2024-01-01&end_date=2024-01-31
```

**Apply suggested categories** — writes high-confidence categories back to the accounting system:

```
POST /api/transactions/categorize/apply
Body: [<list of Transaction objects from the categorize response>]
```

**Detect anomalies** — flags unusual transactions with severity and explanation:

```
GET /api/transactions/anomalies?start_date=2024-01-01&end_date=2024-01-31
```

### Invoices

**Extract invoice data** — upload an image/PDF to extract structured invoice fields:

```
POST /api/invoices/extract
Body: multipart form with file field
```

**Create invoice from extracted data** — creates an invoice in the accounting system:

```
POST /api/invoices/extract/create
Body: <ExtractedInvoice object from the extract response>
```

### Cash flow forecasts

**Generate forecast** — produces a multi-month cash flow forecast with confidence intervals:

```
GET /api/forecasts/cashflow?months=3
```

### Bank reconciliation

**Get match suggestions** — matches unmatched bank transactions to invoices/bills:

```
GET /api/reconciliation/{bank_account_id}?start_date=2024-01-01&end_date=2024-01-31
```

**Apply matches** — writes high-confidence matches to the accounting system:

```
POST /api/reconciliation/apply
Body: {"matches": [<list from suggestions>], "min_confidence": 0.8}
```

### Health check

```
GET /health
```

## Tests

```bash
python -m pytest tests/ -v
```

Tests use a `MockProvider` and `MockLLMClient` — no real credentials needed.

## Architecture

```
app/models/       Canonical Pydantic models (provider-agnostic)
app/providers/    AccountingProvider ABC + Zoho adapter + factory
app/ml/           ML services (depend only on ABC + LLM client)
app/api/          FastAPI routes
```

ML services never import from `app.providers.zoho`. They work entirely through the `AccountingProvider` interface. To add a new backend, implement `AccountingProvider` and register it in `app/providers/factory.py`.
