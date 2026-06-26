# FinAudit Investigator API

> AI-powered fintech support ticket analysis & automated ledger audit engine — built with FastAPI and Google Gemini.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Gemini](https://img.shields.io/badge/Gemini_3.5_Flash-Google_AI-4285F4?logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Overview

FinAudit Investigator is a backend API that automatically **analyzes**, **classifies**, and **triages** digital financial transaction complaints. It combines Google's `gemini-3.5-flash` model with deterministic Python reasoning to cross-reference customer complaints against their transaction ledger history — producing structured, safe, and auditable JSON responses.

### Key Capabilities

- 🔍 **Ledger Cross-Referencing** — Matches complaint text (amounts, phone numbers, timestamps) against transaction history to determine evidence consistency.
- 🏷️ **Automated Case Classification** — Categorizes tickets into 8 case types with severity levels and department routing.
- 🌐 **Multilingual Support** — Handles complaints in English, Bangla, and Banglish with language-appropriate customer replies.
- 🛡️ **Safety Guardrails** — Post-processing filters that prevent credential leaks (PIN/OTP), unauthorized refund promises, and third-party redirects.
- 🤖 **Hybrid AI + Rules Engine** — Deterministic Python logic overrides AI outputs for transaction matching and evidence verdicts, ensuring auditability.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├──────────┬──────────────────────────────────────────────┤
│  Routes  │  POST /analyze-ticket  │  GET /health        │
├──────────┴──────────────────────────────────────────────┤
│                     AI Service Layer                     │
│  ┌──────────────────┐  ┌─────────────────────────────┐  │
│  │ Reasoning Engine │  │ Google Gemini 3.5-Flash API  │  │
│  │  (Deterministic) │  │    (NLP + Classification)    │  │
│  └────────┬─────────┘  └──────────────┬──────────────┘  │
│           │         Merge & Override   │                 │
│           └───────────┬───────────────┘                  │
│                       ▼                                  │
│            ┌─────────────────────┐                       │
│            │    Safety Guard     │                       │
│            │  (Post-Processing)  │                       │
│            └─────────────────────┘                       │
├─────────────────────────────────────────────────────────┤
│  Models: Pydantic Request/Response with Literal enums   │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
finaudit-server/
├── main.py                     # Entry point (uvicorn runner)
├── app/
│   ├── main.py                 # FastAPI app, CORS, exception handlers
│   ├── api/
│   │   └── routes.py           # API endpoint definitions
│   ├── core/
│   │   ├── config.py           # Environment settings (API key, model, port)
│   │   └── logging.py          # Structured JSON logger
│   ├── models/
│   │   ├── request_models.py   # Pydantic input schemas (TicketRequest)
│   │   └── response_models.py  # Pydantic output schemas (TicketResponse)
│   ├── services/
│   │   ├── ai_service.py       # Gemini API integration + orchestration
│   │   ├── reasoning_engine.py # Deterministic verdict & routing logic
│   │   ├── safety_guard.py     # Post-processing security sanitizer
│   │   └── transaction_matcher.py  # Amount/phone extraction & ledger matching
│   └── utils/
├── tests/
│   └── test_api.py             # Unit tests for matcher, reasoning, safety
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variable template
├── docker-compose.yml          # Docker deployment config
└── .gitignore
```

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Gemini API Key** — Get one from [Google AI Studio](https://aistudio.google.com/apikey)

### Installation

```bash
# Clone the repository
git clone https://github.com/Dibakor007/FinAudit-server.git
cd FinAudit-server

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### Run Locally

```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 3000 --reload
```

The API will be available at `http://localhost:3000`. Interactive docs at `http://localhost:3000/docs`.

---

## API Reference

### `GET /health`

Health check endpoint for liveness probes.

**Response** `200 OK`
```json
{ "status": "ok" }
```

---

### `POST /analyze-ticket`

Analyzes a customer support complaint against transaction history.

**Request Body**

```json
{
  "ticket_id": "TKT-B-99",
  "complaint": "আমি ভুল করে ০১৭১২৩৪৫৬৭৮ নাম্বারে ৫০০০ টাকা পাঠিয়েছি। ফেরত দিন।",
  "language": "bn",
  "channel": "in_app_chat",
  "user_type": "customer",
  "campaign_context": null,
  "transaction_history": [
    {
      "transaction_id": "TXN-9101",
      "timestamp": "2026-06-26T14:00:00Z",
      "type": "transfer",
      "amount": 5000.0,
      "counterparty": "+8801712345678",
      "status": "completed"
    }
  ],
  "metadata": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ticket_id` | `string` | ✅ | Unique ticket reference |
| `complaint` | `string` | ✅ | Raw complaint text (non-empty) |
| `language` | `string` | ❌ | Language code (default: `en`) |
| `channel` | `string` | ❌ | Submission channel (default: `in_app_chat`) |
| `user_type` | `string` | ❌ | `customer`, `merchant`, or `agent` |
| `campaign_context` | `string` | ❌ | Campaign identifier |
| `transaction_history` | `array` | ❌ | Array of transaction ledger entries |
| `metadata` | `object` | ❌ | Additional key-value context |

**Response** `200 OK`

```json
{
  "ticket_id": "TKT-B-99",
  "relevant_transaction_id": "TXN-9101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer claims accidental transfer of 5000 BDT to +8801712345678. Ledger confirms a matching completed transaction.",
  "recommended_next_action": "Initiate dispute resolution workflow and contact the recipient for voluntary reversal.",
  "customer_reply": "আমরা আপনার অভিযোগটি পেয়েছি...",
  "human_review_required": true,
  "confidence": 0.92,
  "reason_codes": ["exact_amount_and_recipient_match"]
}
```

**Response Fields**

| Field | Type | Values |
|-------|------|--------|
| `evidence_verdict` | `string` | `consistent` · `inconsistent` · `insufficient_data` |
| `case_type` | `string` | `wrong_transfer` · `payment_failed` · `refund_request` · `duplicate_payment` · `merchant_settlement_delay` · `agent_cash_in_issue` · `phishing_or_social_engineering` · `other` |
| `severity` | `string` | `low` · `medium` · `high` · `critical` |
| `department` | `string` | `customer_support` · `dispute_resolution` · `payments_ops` · `merchant_operations` · `agent_operations` · `fraud_risk` |

**Error Responses**

| Status | Condition |
|--------|-----------|
| `400` | Missing or malformed `ticket_id` / `complaint` |
| `422` | Empty/blank complaint text |
| `500` | Internal server or Gemini API error |

---

## Safety Guardrails

All AI-generated responses are post-processed through three deterministic safety filters:

| Guard | What it does |
|-------|-------------|
| **Credentials Guard** | Rewrites any reply that asks for PIN, OTP, password, or CVV with a standard security warning |
| **Disbursement Guard** | Replaces unauthorized refund promises ("we will refund you") with non-committal language |
| **Redirect Guard** | Strips third-party phone numbers and email addresses, directing users to official channels only |

---

## Testing

```bash
python -m pytest tests/ -v
```

---

## Deployment on Render

1. Push your code to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Connect your repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `GEMINI_API_KEY` — your API key
   - `MODEL_NAME` — `gemini-3.5-flash` (optional)

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ | — | Google AI Studio API key |
| `MODEL_NAME` | ❌ | `gemini-3.5-flash` | Gemini model identifier |
| `PORT` | ❌ | `3000` | Server port |

---

## Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com)** — Async Python web framework
- **[Pydantic v2](https://docs.pydantic.dev)** — Request/response validation with strict Literal types
- **[Google GenAI SDK](https://ai.google.dev/gemini-api/docs)** — Gemini 3.5-Flash structured output generation
- **[Uvicorn](https://www.uvicorn.org)** — ASGI server

---

## License

This project is licensed under the MIT License.
