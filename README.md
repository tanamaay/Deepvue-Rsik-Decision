# Deepvue Risk Decisioning Service

Merchant onboarding and risk decisioning service for loan applications. Verifies businesses against a mock upstream, extracts structured data from unstructured documents, and evaluates against customer-specific credit policies.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐
│  Frontend   │────▶│   API (8000) │────▶│ Mock Upstream  │
│  (React)    │     │   FastAPI    │     │    (8001)      │
│  Port 3000  │     │   SQLite     │     │                │
└─────────────┘     └──────────────┘     └────────────────┘
```

## Quick Start (Docker)

```bash
docker compose up --build
```

- **Frontend:** http://localhost:3000
- **API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Mock Upstream:** http://localhost:8001

## Quick Start (Local, no Docker)

### 1. Mock Upstream
```bash
cd mock-upstream
pip install -r requirements.txt
uvicorn app:app --port 8001
```

### 2. API
```bash
cd api
pip install -r requirements.txt
mkdir -p data
uvicorn app.main:app --port 8000 --reload
```

### 3. Frontend
```bash
cd frontend
npm install
npm run dev
```

## API Keys

| Customer | API Key | Policy |
|----------|---------|--------|
| Kaveri Capital | `kaveri_key_deepvue_2026` | Kaveri v3.1/3.2 |
| Nexa Finserv | `nexa_key_deepvue_2026` | Nexa v1.4 |

Pass via `X-API-Key` header.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/applications` | Submit application (returns immediately) |
| GET | `/v1/applications/{id}` | Get application status and decision |
| GET | `/v1/applications` | List applications (most recent first) |
| GET | `/v1/health` | Service and dependency health |

### Submit Example

```bash
curl -X POST http://localhost:8000/v1/applications \
  -H "X-API-Key: kaveri_key_deepvue_2026" \
  -H "Idempotency-Key: my-unique-key-001" \
  -H "Content-Type: application/json" \
  -d @sample.json
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_OUTAGE` | `false` | Simulate AI model provider outage |
| `KAVERI_POLICY_VERSION` | `3.1` | Switch Kaveri policy to 3.2 |
| `HARD_FAILURE_RATE` | `0.30` | Mock upstream 5xx rate |
| `HANG_RATE` | `0.10` | Mock upstream hang rate |
| `RATE_LIMIT_RATE` | `0.05` | Mock upstream 429 rate |
| `UPSTREAM_MAX_RETRIES` | `3` | Max retry attempts |
| `UPSTREAM_TIMEOUT_SECONDS` | `10` | Per-attempt timeout |

### Toggle without redeploying

```bash
# Simulate model outage
MODEL_OUTAGE=true docker compose up -d api

# Switch Kaveri to policy 3.2
KAVERI_POLICY_VERSION=3.2 docker compose up -d api

# Reduce upstream chaos for testing
HARD_FAILURE_RATE=0 docker compose up -d mock-upstream
```

## Running Tests

```bash
cd api
pip install -r requirements.txt
pytest -v
```

## Database

Uses **SQLite** (file at `api/data/deepvue.db`). Fine for:
- Single-instance deployment
- Demo and take-home assessment
- Low concurrent write volume

**Stops being fine when:**
- Multiple API workers write concurrently (SQLite locks)
- You need replication or point-in-time recovery
- Application volume exceeds ~1000 concurrent writes/min

→ Switch to PostgreSQL for production.

## Sample Variants

The UI includes all Appendix A variants:
- **Sample** — Standard Saraswati Traders application
- **Instruction** — Hostile prompt injection in document
- **Arithmetic** — Turnover expressed as "45 lakh a month" vs declared
- **Sector** — Crypto/virtual digital assets in GST certificate
- **Nothing to read** — Empty unstructured material

## Project Structure

```
├── api/                    # Main risk decisioning API
│   ├── app/
│   │   ├── main.py         # FastAPI entry point
│   │   ├── models.py       # SQLAlchemy models
│   │   ├── policies/       # Policy definitions & engine
│   │   ├── services/       # Upstream, extraction, worker
│   │   └── utils/          # Number normalization
│   └── tests/              # Unit & integration tests
├── mock-upstream/          # Mock verification API
├── frontend/               # React + MUI dashboard
├── docker-compose.yml
├── DECISIONS.md            # Architecture decisions
└── README.md
```
