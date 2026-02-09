# Using ML Accounts with Zoho Books

## Zoho Books basics

Zoho Books is cloud accounting software. Here's what it tracks:

- **Chart of Accounts** — your categories for money movement. Every transaction gets assigned to one. Examples: "Office Supplies" (expense), "Sales Revenue" (income), "Rent" (expense), "Accounts Receivable" (asset). These are set up once and rarely change.

- **Transactions** — every money event. When you pay for something or receive money, it's a transaction. Each one should be assigned to an account from the chart of accounts. This is called "categorization" and is the most tedious part of bookkeeping.

- **Invoices** — bills you send to customers. You create an invoice, send it, and later mark it as paid when money arrives. Statuses: draft → sent → paid/overdue.

- **Bills** — invoices others send to you. Same lifecycle but for money going out.

- **Bank Transactions** — your raw bank feed. Zoho connects to your bank and imports every deposit, withdrawal, and transfer. These need to be "reconciled" — matched to the invoices, bills, or transactions they correspond to.

- **Contacts** — your customers and vendors.

## The problem this system solves

In day-to-day Zoho Books usage, there are several manual, repetitive tasks:

1. **Categorizing transactions** — every transaction needs an account. For a business with hundreds of transactions per month, manually assigning "Office Supplies", "Travel", "Software Subscriptions" etc. is hours of work.

2. **Spotting anomalies** — a duplicate payment, a vendor charging 10x the usual amount, or an unexpected large withdrawal. You'd only catch these by manually reviewing everything.

3. **Cash flow planning** — "will we have enough cash next month?" requires pulling historical data, looking at outstanding invoices/bills, and making educated guesses.

4. **Processing incoming invoices** — vendors email you PDF invoices. Someone has to manually read each one and enter the data into Zoho.

5. **Bank reconciliation** — matching each bank transaction to the invoice or bill it belongs to. Zoho has basic auto-matching but it misses anything that isn't an exact match.

This system automates all five using LLMs.

## Zoho Books setup (one-time)

### 1. Get API credentials

Go to [Zoho API Console](https://api-console.zoho.com/):

1. Create a "Self Client" application
2. Note down the **Client ID** and **Client Secret**
3. Generate a refresh token with these scopes:
   ```
   ZohoBooks.fullaccess.all
   ```
4. Find your **Organization ID** in Zoho Books → Settings → Organization Profile

### 2. Configure ML Accounts

```bash
cp .env.example .env
```

Fill in:
```
ACCOUNTING_PROVIDER=zoho
ZOHO_CLIENT_ID=1000.XXXXXXXXXX
ZOHO_CLIENT_SECRET=abcdef123456
ZOHO_REFRESH_TOKEN=1000.xxxxx.xxxxx
ZOHO_ORG_ID=12345678

LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o
```

### 3. Start the server

```bash
uvicorn app.main:app --reload
```

## Workflows

### Workflow 1: Monthly transaction categorization

**When**: End of week or end of month, after transactions have accumulated in Zoho.

**The problem**: You imported 200 bank transactions this month. Each one needs to be assigned to the right account (Office Supplies, Rent, Software, etc.). Doing this manually takes hours.

**Steps**:

1. **Get categorization suggestions**:

```bash
curl "http://localhost:8000/api/transactions/categorize?start_date=2024-01-01&end_date=2024-01-31"
```

This pulls all uncategorized transactions from Zoho for that date range, sends them to the LLM along with your chart of accounts, and returns each transaction with a suggested `account_id`, `account_name`, and `confidence` score (0.0–1.0).

Response:
```json
[
  {
    "id": "txn_123",
    "description": "AMAZON WEB SERVICES",
    "amount": 450.00,
    "account_id": "acc_software",
    "account_name": "Software Subscriptions",
    "category": "Software Subscriptions",
    "confidence": 0.95
  },
  {
    "id": "txn_124",
    "description": "UBER TRIP 4829",
    "amount": 32.50,
    "account_id": "acc_travel",
    "account_name": "Travel & Transport",
    "category": "Travel & Transport",
    "confidence": 0.88
  }
]
```

2. **Review and apply**: Look through the suggestions. If they look good, apply them — this writes the categories back to Zoho:

```bash
curl -X POST "http://localhost:8000/api/transactions/categorize/apply" \
  -H "Content-Type: application/json" \
  -d '[... the response from step 1 ...]'
```

Only transactions with confidence >= 0.7 get written back. Low-confidence ones are skipped so you can handle them manually in Zoho.

**Typical schedule**: Run weekly or at month-end during your bookkeeping routine.

---

### Workflow 2: Anomaly detection

**When**: Monthly review, or before sending reports to your accountant.

**The problem**: Buried in hundreds of transactions are a few that are wrong — a vendor double-charged you, someone expensed something unusual, or a payment went to the wrong place. You'd only find these by reading every line.

**Steps**:

```bash
curl "http://localhost:8000/api/transactions/anomalies?start_date=2024-01-01&end_date=2024-01-31"
```

The system computes statistics (average amounts per vendor, per category) and asks the LLM to flag anything unusual.

Response:
```json
[
  {
    "transaction": {
      "id": "txn_456",
      "description": "ACME CORP PAYMENT",
      "amount": 75000.00,
      "contact_name": "Acme Corp"
    },
    "is_anomaly": true,
    "severity": "high",
    "reason": "Amount is 15x the average payment to Acme Corp ($5,000). Possible duplicate or error.",
    "score": 0.95
  }
]
```

You then investigate each flagged item in Zoho Books and fix any real issues.

**Typical schedule**: Monthly, before closing the books.

---

### Workflow 3: Cash flow forecasting

**When**: Planning meetings, before making big purchases, or monthly financial reviews.

**The problem**: "Can we afford to hire someone next month?" requires looking at historical revenue patterns, outstanding invoices (money coming in), and unpaid bills (money going out), then projecting forward.

**Steps**:

```bash
curl "http://localhost:8000/api/forecasts/cashflow?months=3"
```

The system pulls 12 months of transaction history from Zoho, aggregates monthly inflows/outflows, and also pulls open invoices (expected income) and unpaid bills (expected expenses). The LLM produces a monthly forecast with confidence intervals.

Response:
```json
{
  "generated_at": "2024-02-15T10:30:00",
  "periods": [
    {
      "start_date": "2024-03-01",
      "end_date": "2024-03-31",
      "predicted_inflow": 45000.00,
      "predicted_outflow": 32000.00,
      "net": 13000.00,
      "confidence_low": 8000.00,
      "confidence_high": 18000.00
    },
    {
      "start_date": "2024-04-01",
      "end_date": "2024-04-30",
      "predicted_inflow": 42000.00,
      "predicted_outflow": 35000.00,
      "net": 7000.00,
      "confidence_low": 2000.00,
      "confidence_high": 12000.00
    }
  ],
  "summary": "Cash flow is expected to remain positive over the next 3 months. March looks strong due to two large outstanding invoices ($15K from Acme Corp, $10K from Beta Inc). April may tighten as annual software renewals come due."
}
```

**Typical schedule**: Monthly, or ad hoc before financial decisions.

---

### Workflow 4: Invoice data extraction

**When**: Whenever you receive a PDF or image invoice from a vendor.

**The problem**: A vendor emails you an invoice PDF. Someone needs to open it, read the vendor name, invoice number, line items, amounts, and tax, then manually type all of that into Zoho Books as a new bill. For businesses receiving dozens of invoices per month, this is tedious and error-prone.

**Steps**:

1. **Extract data from the file**:

```bash
curl -X POST "http://localhost:8000/api/invoices/extract" \
  -F "file=@/path/to/invoice.pdf"
```

The system sends the file to the LLM's vision API, which reads and structures all the data.

Response:
```json
{
  "vendor_name": "CloudHost Inc",
  "invoice_number": "CH-2024-0892",
  "date": "2024-01-15",
  "due_date": "2024-02-15",
  "total": 2400.00,
  "tax": 200.00,
  "lines": [
    {"description": "Dedicated Server - January", "quantity": 1, "rate": 1800.00, "amount": 1800.00},
    {"description": "SSL Certificates (x3)", "quantity": 3, "rate": 66.67, "amount": 200.00}
  ],
  "raw_text": "..."
}
```

2. **Review, then create in Zoho**:

```bash
curl -X POST "http://localhost:8000/api/invoices/extract/create" \
  -H "Content-Type: application/json" \
  -d '{ ... the response from step 1 ... }'
```

This creates the invoice in Zoho Books, matching the vendor to an existing contact if possible.

**Typical schedule**: As invoices arrive, or in a batch at end of week.

---

### Workflow 5: Bank reconciliation

**When**: Weekly or monthly, after bank transactions have been imported into Zoho.

**The problem**: Your bank feed shows "ACH DEPOSIT — ACME CORP $5,000" and you have an open invoice to Acme Corp for $5,000. A human can see these match, but Zoho's auto-matching often misses them when the descriptions don't match exactly. You end up manually clicking through hundreds of bank transactions to pair them.

**Steps**:

1. **Get match suggestions** (you need a bank account ID from Zoho — find it in Zoho Books → Banking):

```bash
curl "http://localhost:8000/api/reconciliation/BANK_ACCOUNT_ID?start_date=2024-01-01&end_date=2024-01-31"
```

The system pulls unmatched bank transactions and open invoices/bills from Zoho, then uses the LLM to match them by amount, date proximity, reference numbers, and description similarity.

Response:
```json
[
  {
    "bank_transaction": {
      "id": "bt_789",
      "date": "2024-01-21",
      "amount": 5000.00,
      "description": "ACH DEPOSIT ACME CORP"
    },
    "matched_entity": {
      "id": "inv_001",
      "number": "INV-001",
      "total": 5000.00,
      "contact_name": "Acme Corp"
    },
    "match_type": "exact_amount",
    "confidence": 0.95,
    "reasoning": "Exact amount match ($5,000), description contains customer name, dates within 2 days."
  }
]
```

2. **Review and apply**:

```bash
curl -X POST "http://localhost:8000/api/reconciliation/apply" \
  -H "Content-Type: application/json" \
  -d '{"matches": [... from step 1 ...], "min_confidence": 0.8}'
```

Only matches above the confidence threshold get applied in Zoho. Lower-confidence matches are left for manual review.

**Typical schedule**: Weekly, as part of your bank reconciliation routine.

## Suggested monthly routine

| When | What | Endpoint |
|------|------|----------|
| Weekly | Reconcile bank transactions | `GET /api/reconciliation/{id}` → `POST /api/reconciliation/apply` |
| Weekly | Process received invoices | `POST /api/invoices/extract` → `POST /api/invoices/extract/create` |
| End of month | Categorize transactions | `GET /api/transactions/categorize` → `POST /api/transactions/categorize/apply` |
| End of month | Check for anomalies | `GET /api/transactions/anomalies` |
| Monthly / ad hoc | Forecast cash flow | `GET /api/forecasts/cashflow` |

## How data flows

```
Zoho Books (source of truth)
    │
    ▼
AccountingProvider (abstract interface)
    │
    ▼
ML Services (categorizer, anomaly detector, etc.)
    │  ├── reads data from provider
    │  ├── sends to LLM for analysis
    │  └── returns suggestions
    │
    ▼
API endpoints (you call these)
    │
    ▼
Apply endpoints (write approved changes back to Zoho)
```

The system never modifies Zoho data without you explicitly calling an "apply" endpoint. The `GET` endpoints are read-only suggestions. The `POST /apply` endpoints write back.
