# MuleShield AI

## AI-Powered Mule Account Detection & Fraud Prevention System

**Built for the Bank of India Hackathon 2026 — IIT Hyderabad**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)]()
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)]()
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-EC4C3B)]()
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3-EE4C2C?logo=pytorch&logoColor=white)]()

---

MuleShield AI is an enterprise-grade, real-time fraud detection system designed specifically for Public Sector Banks in India. It detects **mule accounts** — accounts used to funnel stolen funds — by combining **six machine learning models** into a weighted ensemble that produces a **Risk Score from 0 to 1000** with full explainability.

> **Problem:** Mule accounts are the backbone of financial fraud in India. With thousands of new accounts opened daily across PSBs, manual detection is impossible. Fraudsters use smurfing, layering, and structuring across multiple accounts to launder money undetected.
>
> **Solution:** MuleShield AI ingests account feature vectors, scores them in real time using a parallelized 6-model ensemble, explains every decision via SHAP, generates regulatory STR drafts (goAML), and optionally auto-freezes critical accounts — all with an immutable SHA-256 chained audit trail.

---

## Features

### Core Capabilities

- **6-Model Ensemble Scoring** — XGBoost, LightGBM, CatBoost, Isolation Forest, PyTorch Autoencoder, and GNN in parallel
- **Risk Score (0–1000)** with five bands: MINIMAL, LOW, MEDIUM, HIGH, CRITICAL
- **SHAP Explainability** — every score includes top-10 feature attributions with direction
- **Detection Pattern Classification** — identifies Smurfing, Structuring, Layering, Round-Tripping, Account Takeover, Synthetic Identity, and 5 more fraud typologies
- **Auto-Freeze Engine** — CRITICAL accounts are automatically hard-frozen with kill-switch override
- **goAML STR Draft Generation** — pre-filled Suspicious Transaction Reports for regulatory submission
- **Immutable Audit Trail** — SHA-256 hash-chained logging, regulator-verifiable
- **Kill Switch** — emergency stop for all automated actions
- **Redis-Backed Caching** — sub-millisecond cache hits with in-process fallback

### Performance Optimizations

| Optimization | Technique | Impact |
|-------------|-----------|--------|
| Model Inference | ThreadPoolExecutor parallelism | Latency = max(model) not sum(model) |
| SHAP Computation | TreeExplainer created once at startup, cached | 100–500ms saved per request |
| Audit Logging | In-memory hash chain caching | 1 DB round-trip instead of 2 |
| Score Cache | Redis-backed with in-process fallback | Sub-ms cache hits, shared across workers |
| DB Connection | Connection pooling (10/20), SQLite WAL mode | 5x concurrent throughput |
| NaN Imputation | Vectorized `np.where` | Eliminates per-column Python loop |
| Batch Prediction | Vectorized model predict (no row-by-row) | O(n×m) → O(m) |
| Training | All 5 models train concurrently | Wall time = max(individual) |
| Regulator Summary | Single `GROUP BY` query | 7 DB queries → 3 |

### Fraud Detection Patterns

| Pattern | Typical Score Range | Description |
|---------|-------------------|-------------|
| Smurfing | 500–750 | Breaking large amounts into small transactions |
| Structuring | 500–700 | Multiple deposits just below reporting threshold |
| Rapid Fund Movement | 600–800 | Fast credit-debit cycles through an account |
| Round Tripping | 600–800 | Funds returning to source after circuitous route |
| Layering | 700–900 | Multiple hops through intermediate accounts |
| Cash In / Cash Out | 550–700 | Cash deposits followed by immediate withdrawal |
| Dormant Activation | 400–600 | Long-dormant account suddenly active |
| Account Takeover | 700–900 | Unusual device/login patterns |
| Synthetic Identity | 800–1000 | Artificial identity using fabricated KYC |
| Multi-Account Abuse | 600–800 | Same user operating many accounts |
| Cross-Channel Laundering | 800–1000 | Laundering across UPI, NEFT, IMPS, cash |

---

## Architecture

```
┌──────────────┐     ┌──────────────────────────────────────┐     ┌──────────┐
│  React UI    │────▶│          FastAPI Backend             │────▶│ SQLite   │
│  Dashboard   │     │  ┌────────────────────────────────┐  │     │ Postgres │
│              │     │  │  /api/v1/score                 │  │     │ (prod)   │
│  • Alerts    │     │  │  /api/v1/alerts                │  │     └──────────┘
│  • Account   │     │  │  /api/v1/action                │  │
│    Detail    │     │  │  /api/v1/regulator/summary     │  │     ┌──────────┐
│  • SHAP      │     │  │  /api/v1/audit                 │  │     │  Redis   │
│    Charts    │     │  │  /api/v1/kill-switch           │  │     │  Cache   │
│  • Freeze    │     │  └────────────────────────────────┘  │     └──────────┘
│    Controls  │     │  ┌────────────────────────────────┐  │
└──────────────┘     │  │   Ensemble Engine              │  │     ┌──────────┐
                     │  │  ┌─────┐ ┌─────┐ ┌───────┐   │  │     │ MLflow   │
                     │  │  │ XGB │ │ LGB │ │ CatB  │   │  │     │ Tracking │
                     │  │  └─────┘ └─────┘ └───────┘   │  │     └──────────┘
                     │  │  ┌─────┐ ┌─────┐ ┌───────┐   │  │
                     │  │  │ IF  │ │ AE  │ │ GNN*  │   │  │     ┌──────────┐
                     │  │  └─────┘ └─────┘ └───────┘   │  │     │Model     │
                     │  │  *GNN: optional (graph data) │  │     │Artifacts │
                     │  └────────────────────────────────┘  │     └──────────┘
                     │  ┌────────────────────────────────┐  │
                     │  │  SHAP Explainer (cached)       │  │
                     │  │  Prevention Engine             │  │
                     │  │  Audit Service (SHA-256 chain) │  │
                     │  │  STR Generator (goAML)         │  │
                     │  └────────────────────────────────┘  │
                     └──────────────────────────────────────┘
```

### ML Ensemble Weights

| Model | Weight | Role |
|-------|--------|------|
| XGBoost | 30% | Primary gradient booster |
| LightGBM | 25% | Leaf-wise gradient booster |
| CatBoost | 15% | Ordered boosting for categoricals |
| Isolation Forest | 15% | Unsupervised anomaly detection |
| Autoencoder (PyTorch) | 10% | Reconstruction error anomaly |
| GNN | 5% | Graph topology (optional) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI 0.111 |
| **ML Ensemble** | XGBoost 2.0, LightGBM 4.3, CatBoost 1.2 |
| **Anomaly Detection** | scikit-learn Isolation Forest |
| **Deep Learning** | PyTorch 2.3 (Autoencoder) |
| **Explainability** | SHAP 0.45 |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Cache** | Redis 5.0 |
| **ORM** | SQLAlchemy 2.0 |
| **Frontend** | React 18 + TypeScript + Vite + TailwindCSS |
| **Monitoring** | Prometheus + Grafana |
| **Experiment Tracking** | MLflow 2.14 |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- Redis (optional — falls back to in-process cache)

### 1. Clone & Setup Backend

```bash
git clone https://github.com/guru-murtthy/MuleShield-AI.git
cd MuleShield-AI/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Train the Model

```bash
# Provide your DataSet.csv path (9,082 x 3,924 anonymized feature matrix)
python scripts/train.py --data /path/to/DataSet.csv

# With MLflow tracking (optional)
python scripts/train.py --data /path/to/DataSet.csv --mlflow-uri http://localhost:5000
```

Training auto-detects the label column, handles NaN imputation (vectorized), drops high-missing/constant columns, splits stratified 80/20, trains all 5 models in parallel, and saves artifacts to `./artifacts/`.

### 3. Start the API Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API auto-loads trained models on startup.

### 4. Start the Frontend Dashboard

```bash
cd frontend
npm install
npm run start
```

Opens at `http://localhost:5173`. The dashboard auto-connects to the API at `http://localhost:8000`.

---

## API Reference

All endpoints are under `/api/v1/`. Full interactive docs at `http://localhost:8000/docs`.

### `POST /api/v1/score`
Submit an account for fraud risk scoring.

```json
{
  "account_id": "ACC-001234",
  "features": [0.5, 0.2, 0.0, ...]
}
```

Returns Risk Score (0–1000), Risk Band, ensemble probability, per-model probabilities, detection patterns, SHAP top-10 features, narrative, auto-freeze eligibility, and optional goAML STR draft.

### `GET /api/v1/alerts`
Paginated alert queue (Risk Band >= MEDIUM), sorted by score descending.

### `POST /api/v1/action`
Apply freeze/unfreeze/fund_trace action with analyst attribution.

### `GET /api/v1/regulator/summary`
Regulatory metrics (requires `X-Regulator-Token` header).

### `GET /api/v1/audit`
Immutable, paginated audit log with event type and account filters.

### `POST /api/v1/kill-switch`
Emergency stop for automated freeze actions.

### `GET /api/v1/health`
Service health and model status.

### `GET /metrics`
Prometheus metrics endpoint.

---

## Configuration

Set via environment variables (`.env` file in `backend/`):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./muleshield.db` | Database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `MODEL_ARTIFACTS_DIR` | `./artifacts` | Trained model storage |
| `SCORE_CACHE_TTL` | `60` | Score cache TTL (seconds) |
| `REGULATOR_TOKEN` | `regulator-secret-token` | API auth for regulator endpoint |
| `KILL_SWITCH_ACTIVE` | `False` | Global kill switch flag |
| `XGBOOST_WEIGHT` | `0.30` | Ensemble weight overrides |
| `DEBUG` | `False` | Debug mode |

---

## Project Structure

```
MuleShield-AI/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes.py        # FastAPI endpoints
│   │   │   └── schemas.py       # Pydantic request/response models
│   │   ├── core/
│   │   │   ├── config.py        # Settings via pydantic-settings
│   │   │   └── database.py      # SQLAlchemy engine with WAL + pooling
│   │   ├── ml/
│   │   │   ├── ensemble.py      # 6-model ensemble with parallel inference
│   │   │   ├── scorer.py        # Risk scoring, SHAP, patterns, STR
│   │   │   └── preprocessor.py  # Dataset loading + vectorized cleaning
│   │   ├── models/
│   │   │   └── db_models.py     # ScoreRecord, AccountAction, AuditLog
│   │   ├── services/
│   │   │   ├── model_service.py # Singleton model loader + cached SHAP
│   │   │   ├── audit_service.py # SHA-256 chained audit with in-memory hash
│   │   │   └── prevention_service.py  # Freeze engine + kill switch
│   │   └── main.py              # FastAPI entry point with Prometheus
│   ├── scripts/
│   │   └── train.py             # Training pipeline (parallel model fit)
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # AlertQueue, AccountDetail, SHAPChart, RiskBadge
│   │   ├── pages/               # Dashboard (alert queue + detail panel)
│   │   ├── utils/               # API client (axios)
│   │   └── types/               # TypeScript interfaces
│   └── package.json
├── docker/                      # Docker build files
├── monitoring/                  # Prometheus + Grafana configs
└── docs/                        # Documentation
```

---

## Security & Compliance

- **SHA-256 Hash Chaining** — every audit record includes the hash of the previous record, forming an immutable chain verifiable by regulators
- **JWT Authentication** — API endpoints secured with Bearer tokens (via python-jose)
- **Kill Switch** — one-button emergency stop for all automated freeze actions, logged immutably
- **Role-Based Access** — analyst dashboard vs regulator read-only endpoint
- **Audit Trail** — every score, freeze, and action is permanently recorded
- **goAML STR Generation** — pre-filled Suspicious Transaction Reports matching regulatory format

---

## Monitoring

Prometheus metrics at `/metrics`:

- `muleshield_requests_total` — request count by method and endpoint
- `muleshield_score_latency_seconds` — score endpoint latency histogram

Pre-configured Grafana dashboard templates in `monitoring/grafana/`.

---

## Built For

**Bank of India Hackathon 2026** at **Indian Institute of Technology Hyderabad**

Team: [Yoodha]

MuleShield AI addresses the critical challenge of mule account detection in India's public banking sector — combining ensemble ML, explainable AI, and regulatory compliance into a production-ready fraud prevention platform.

---

## License

This project is submitted for the Bank of India Hackathon 2026 at IIT Hyderabad.
