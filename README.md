<![CDATA[<div align="center">

# ⚡ FluxLogic — Engineering-led Data Automation

**Universal Data Connector · Upload · Process · Dispatch**

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)](https://docs.pydantic.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e)](LICENSE)

*A SaaS-ready proof of concept built to demonstrate end-to-end data pipeline engineering — from ingestion to API dispatch — with enterprise-grade validation, resilience, and observability.*

</div>

---

## 📌 Problem Statement

Modern SaaS companies rely on dozens of third-party services (CRM, analytics, billing, notifications). Moving data between these systems is often handled by brittle, ad-hoc scripts that lack:

- **Schema validation** — bad data propagates silently.
- **Retry logic** — transient API failures cause data loss.
- **Auditability** — no record of what was sent, when, or to whom.

**FluxLogic** solves this by providing a single, configurable data connector that cleans, validates, and reliably dispatches data to any REST API — with full audit logging and webhook support.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  Upload   │  │ Dispatch │  │ Webhooks │  │  Flow Log   │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬──────┘ │
│       │              │              │               │        │
├───────┼──────────────┼──────────────┼───────────────┼────────┤
│       ▼              ▼              ▼               ▼        │
│  ┌─────────┐   ┌──────────┐  ┌───────────┐  ┌───────────┐  │
│  │Processor│   │ApiClient │  │ Webhook   │  │ Models /   │  │
│  │ (ETL)   │   │(Requests)│  │ Manager   │  │  Logging   │  │
│  └─────────┘   └──────────┘  └───────────┘  └───────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │          config.py  (pydantic-settings + .env)       │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Module Breakdown

| Module | Responsibility |
|---|---|
| `config.py` | Centralized settings via `pydantic-settings`. Reads from environment variables / `.env` file with strict validation at startup. |
| `models.py` | Pydantic v2 schemas for every data structure: `ApiEndpoint`, `BatchResult`, `WebhookEvent`, `FlowLogEntry`, etc. |
| `processor.py` | `DataProcessor` class — a multi-stage ETL pipeline (strip → normalize → coerce → dedup → validate). |
| `api_client.py` | Resilient HTTP client with automatic retries, exponential backoff, timeout handling, and batch dispatch. |
| `webhooks.py` | `WebhookManager` — HMAC-SHA256 signing/verification, outbound delivery, and inbound simulation. |
| `fluxlogic_app.py` | Streamlit UI — the dashboard that ties everything together. |

---

## 🛠️ Tech Stack & Rationale

| Technology | Why |
|---|---|
| **Python 3.11+** | Type hints, pattern matching, performance improvements. Industry standard for data engineering. |
| **Streamlit** | Rapid UI prototyping with zero frontend code. Ideal for PoC / internal tools where time-to-demo matters. |
| **Pydantic v2** | Strict runtime validation with compile-time type checking. Prevents malformed data from entering the pipeline. |
| **pydantic-settings** | Twelve-factor app configuration: environment variables validated at startup, not at first use. |
| **Requests + urllib3** | Battle-tested HTTP client with built-in retry strategies and connection pooling. |
| **Pandas** | Efficient tabular data manipulation for CSV/JSON ingestion and deduplication. |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-username/fluxlogic.git
cd fluxlogic

python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your settings (all optional — defaults work out of the box)
```

### 3. Run

```bash
streamlit run fluxlogic_app.py
```

The dashboard opens at `http://localhost:8501`.

---

## 📖 Usage Guide

### Uploading Data
1. Go to the **Data Upload** tab.
2. Upload a `.csv` or `.json` file, or paste JSON manually.
3. Click **Run Processing Pipeline** to clean and validate records.

### Configuring Endpoints
1. In the **sidebar**, expand *Add New Endpoint*.
2. Fill in the target URL, HTTP method, optional API key, and custom headers.
3. Save — endpoints persist for the session.

### Dispatching Data
1. After processing, switch to the **API Dispatch** tab.
2. Select a configured endpoint and click **Dispatch Now**.
3. Results (status code, latency, errors) appear inline.

### Webhook Simulation
1. Use the **Webhooks** tab to simulate inbound events or send outbound webhooks.
2. All events are HMAC-signed and logged in the event history.

---

## 🔐 Security & Resilience

- **HMAC-SHA256** signature verification on all webhook payloads.
- **Exponential backoff** with configurable retry counts (default: 3 retries).
- **Timeout enforcement** on every outbound HTTP call (default: 30 s).
- **Input validation** via Pydantic — malformed data is rejected before dispatch.
- **API keys** are masked in the UI (`type="password"`) and sent as `Authorization: Bearer` headers.

---

## 📈 SaaS Scalability Considerations

Although this is a proof of concept, the architecture is designed with production scalability in mind:

| Concern | Current (PoC) | Production Path |
|---|---|---|
| **Task queue** | Synchronous dispatch | Celery / Redis workers |
| **Data store** | In-memory session state | PostgreSQL + SQLAlchemy |
| **Auth** | None (local tool) | OAuth 2.0 / JWT via FastAPI |
| **Deployment** | `streamlit run` | Docker → Kubernetes / Cloud Run |
| **Observability** | Python logging | OpenTelemetry + Grafana |
| **Rate limiting** | urllib3 retry | Token-bucket / leaky-bucket |

---

## 🧪 Testing

```bash
# Run unit tests (when added)
python -m pytest tests/ -v --cov=.

# Type checking
mypy . --strict
```

---

## 📁 Project Structure

```
FluxLogic/
├── fluxlogic_app.py      # Streamlit dashboard (entry point)
├── config.py              # pydantic-settings configuration
├── models.py              # Pydantic v2 data schemas
├── processor.py           # DataProcessor ETL engine
├── api_client.py          # Resilient HTTP dispatch client
├── webhooks.py            # Webhook manager (sign / send / verify)
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
└── README.md              # This file
```

---

## 👤 Author

**EPITA Engineering Student** — Bac+3, Titre RNCP 40531

This project demonstrates competencies in:
- **Software Architecture** — modular, layered design with clear separation of concerns.
- **Data Engineering** — ETL pipeline with validation, normalization, and error handling.
- **API Integration** — resilient HTTP clients with retry/backoff strategies.
- **DevOps Mindset** — twelve-factor configuration, environment isolation, production-ready patterns.

---

<div align="center">

**Built with ❤️ and Python**

*FluxLogic — Because data should flow, not break.*

</div>

