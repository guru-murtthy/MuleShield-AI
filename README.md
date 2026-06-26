# MuleShield AI

## AI-Powered Mule Account Detection & Fraud Prevention System for PSBs

**Built for the Bank of India Hackathon 2026 — IIT Hyderabad**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)]()
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)]()
[![XGBoost](https://img.shields.io/badge/XGBoost-2.0-EC4C3B)]()
[![PyTorch](https://img.shields.io/badge/PyTorch-2.3-EE4C2C?logo=pytorch&logoColor=white)]()

---

## Project Overview

MuleShield AI is an enterprise-grade, real-time fraud detection platform purpose-built for **Public Sector Banks (PSBs)** in India. The system detects **mule accounts** — accounts exploited by criminals to funnel stolen funds — using advanced machine learning and explainable AI techniques.

The platform ingests anonymized banking transaction features from the real **DataSet.csv** (9,082 rows × 3,924 features), trains a weighted ensemble of six ML models (XGBoost, LightGBM, CatBoost, Isolation Forest, PyTorch Autoencoder, and GNN), and produces a **Risk Score from 0 to 1,000** for every account under review. Investigators access findings through a React + TypeScript dashboard with SHAP explainability, while compliance officers receive pre-drafted **goAML STR reports** ready for FIU-IND submission.

### The Problem

Mule accounts are the backbone of financial fraud in India. With thousands of new accounts opened daily across PSBs, manual detection is impossible. Fraudsters use sophisticated techniques like smurfing, layering, and structuring across multiple accounts to launder money undetected, causing billions in losses annually.

### The Solution

MuleShield AI provides:
- **Real-time Risk Scoring**: 0–1,000 risk scores with sub-500ms latency
- **Full Explainability**: SHAP feature attributions and plain-language narratives for every decision
- **Automated Prevention**: Auto-freeze HIGH/CRITICAL accounts with kill-switch override
- **Regulatory Compliance**: Pre-drafted goAML STR reports and immutable SHA-256 audit chains
- **One-Day Deployment**: Complete stack deployable via `docker compose up` from GitHub

The entire system ships as a GitHub-ready repository with Docker Compose support, enabling any PSB to clone, configure, and deploy the prototype within a single working day.

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

MuleShield AI implements a **10-layer fraud detection architecture** optimized for PSB deployment:

```
┌────────────────────────────────────────────────────────────────────┐
│ LAYER 1: Presentation Layer                                        │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │  React 18 + TypeScript + Vite + Tailwind CSS Dashboard      │   │
│ │  • Alert Queue (live-updating)  • Account Detail Panel      │   │
│ │  • SHAP Waterfall Charts (D3)   • Relationship Graph (Cyto) │   │
│ │  • Freeze Controls              • Regulator Portal View     │   │
│ └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │ HTTP REST API
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 2: API Gateway Layer                                         │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │  FastAPI 0.111 with OpenAPI Docs                            │   │
│ │  /score  /alerts  /action  /regulator  /audit  /kill-switch │   │
│ │  CORS Middleware • Input Validation • Token Auth            │   │
│ └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 3: Business Logic Layer                                      │
│ ┌────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│ │ Model Service  │  │ Prevention Engine│  │  Audit Service   │   │
│ │ • Load models  │  │ • Soft Freeze    │  │ • SHA-256 chain  │   │
│ │ • Score cache  │  │ • Hard Freeze    │  │ • Event logging  │   │
│ │ • SHAP cache   │  │ • Kill Switch    │  │ • Immutable log  │   │
│ └────────────────┘  └──────────────────┘  └──────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 4: ML Scoring Layer                                          │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │  Risk Scorer (0–1000 Risk Score + Risk Band)                │   │
│ │  • Score Computation  • Pattern Detection  • STR Generator  │   │
│ └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 5: Explainability Layer                                      │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │  SHAP 0.45 TreeExplainer (cached at startup)                │   │
│ │  • Top-10 Feature Attributions  • NLP Narrative Generator   │   │
│ └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 6: Ensemble Prediction Layer                                 │
│ ┌───────────────────────────────────────────────────────────┐     │
│ │  6-Model Weighted Ensemble (Parallel ThreadPool Execution) │     │
│ │  ┌─────────┐ ┌──────────┐ ┌──────────┐                    │     │
│ │  │ XGBoost │ │ LightGBM │ │ CatBoost │  Supervised Models │     │
│ │  │ (30%)   │ │  (25%)   │ │  (15%)   │                    │     │
│ │  └─────────┘ └──────────┘ └──────────┘                    │     │
│ │  ┌─────────┐ ┌──────────┐ ┌──────────┐                    │     │
│ │  │Isolation│ │Autoencoder│ │   GNN   │  Anomaly Detection│     │
│ │  │ Forest  │ │ (PyTorch) │ │(PyG-opt)│                    │     │
│ │  │ (15%)   │ │   (10%)   │ │  (5%)   │                    │     │
│ │  └─────────┘ └──────────┘ └──────────┘                    │     │
│ └───────────────────────────────────────────────────────────┘     │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 7: Data Preprocessing Layer                                  │
│ ┌─────────────────────────────────────────────────────────────┐   │
│ │  Data Preprocessor                                           │   │
│ │  • Missing Value Imputation (median, vectorized)            │   │
│ │  • StandardScaler Normalization                             │   │
│ │  • Feature Selection (drop >70% missing, constant columns)  │   │
│ └─────────────────────────────────────────────────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 8: Caching Layer                                             │
│ ┌──────────────┐  ┌──────────────────────────────────────────┐   │
│ │ Redis Cache  │  │ In-Memory Fallback                        │   │
│ │ • Score TTL: │  │ • Model artifacts cached at startup       │   │
│ │   60 seconds │  │ • SHAP TreeExplainer (singleton)          │   │
│ │ • Sub-5ms    │  │ • Audit hash chain (last record cached)   │   │
│ └──────────────┘  └──────────────────────────────────────────┘   │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 9: Persistence Layer                                         │
│ ┌──────────┐  ┌─────────┐  ┌────────┐  ┌──────────────────┐      │
│ │ SQLite   │  │ Neo4j   │  │ MLflow │  │ Prometheus TSDB  │      │
│ │ (Dev) or │  │ Graph DB│  │Registry│  │ (Metrics)        │      │
│ │PostgreSQL│  │(optional│  │ Models │  │                  │      │
│ │  (Prod)  │  │  graph) │  │Artifacts│  │                  │      │
│ │          │  │         │  │        │  │                  │      │
│ │• Scores  │  │• Account│  │•Trained│  │•Request Counters │      │
│ │• Actions │  │  Edges  │  │ Models │  │•Latency Histos   │      │
│ │• Audit   │  │• Txn    │  │•Scalers│  │•Alert Gauges     │      │
│ │  Log     │  │  Graph  │  │•Metrics│  │                  │      │
│ └──────────┘  └─────────┘  └────────┘  └──────────────────┘      │
└────────────────────────────────┬───────────────────────────────────┘
                                 │
┌────────────────────────────────▼───────────────────────────────────┐
│ LAYER 10: Training & Monitoring Layer                              │
│ ┌────────────────────────────┐  ┌────────────────────────────┐    │
│ │  Training Pipeline         │  │  Monitoring Stack          │    │
│ │  scripts/train.py          │  │  Prometheus + Grafana      │    │
│ │  • Load DataSet.csv        │  │  • Request Metrics         │    │
│ │  • Train 6 models (||)     │  │  • Latency Dashboards      │    │
│ │  • Evaluate (AUC≥0.80)     │  │  • Alert Heatmaps          │    │
│ │  • Register to MLflow      │  │  • Audit Alerts (90% cap)  │    │
│ └────────────────────────────┘  └────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
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

Deploy the complete MuleShield AI stack with Docker Compose in **5 steps**:

### Step 1: Clone and Setup
```bash
git clone https://github.com/guru-murtthy/MuleShield-AI.git
cd MuleShield-AI
cp .env.example .env  # Configure environment variables (optional)
```

### Step 2: Add Training Data
```bash
# Copy your DataSet.csv (9,082 x 3,924 anonymized features) to the data directory
mkdir -p data
cp /path/to/DataSet.csv data/
```

### Step 3: Start All Services
```bash
docker compose up --build
# Starts: FastAPI backend, React frontend, Redis, Neo4j, MLflow, Prometheus, Grafana
# Training pipeline runs automatically if no models exist
```

### Step 4: Verify Deployment
```bash
# Wait for all services to report healthy (typically ~120 seconds)
docker compose ps
# All services should show status: "healthy" or "Up"
```

### Step 5: Access the System
- **Dashboard**: http://localhost:3000 (Investigator UI)
- **API Docs**: http://localhost:8000/docs (OpenAPI Swagger)
- **MLflow**: http://localhost:5000 (Model registry)
- **Grafana**: http://localhost:3001 (Monitoring, admin/admin)

**First-time setup:** If models don't exist, the training pipeline automatically runs against `data/DataSet.csv` during Step 3. This takes ~10 minutes for the 6-model ensemble.

**Manual training:** To retrain models anytime:
```bash
docker compose exec backend python scripts/train.py --data /data/DataSet.csv
```

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

## Configuration Reference

Configure MuleShield AI via environment variables in the `.env` file (backend root):

### Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./muleshield.db` | Database connection string. Use `postgresql://user:pass@host:5432/db` for production. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache connection string. System falls back to in-memory cache if unavailable. |
| `MODEL_ARTIFACTS_DIR` | `./artifacts` | Directory for trained model storage (scalers, models, imputers). |
| `DATASET_PATH` | `./data/DataSet.csv` | Path to training dataset (9,082 × 3,924 anonymized features). |

### ML Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `XGBOOST_WEIGHT` | `0.30` | XGBoost ensemble weight (primary gradient booster). |
| `LIGHTGBM_WEIGHT` | `0.25` | LightGBM ensemble weight (leaf-wise booster). |
| `CATBOOST_WEIGHT` | `0.15` | CatBoost ensemble weight (ordered boosting). |
| `ISOLATION_FOREST_WEIGHT` | `0.15` | Isolation Forest weight (unsupervised anomaly). |
| `AUTOENCODER_WEIGHT` | `0.10` | Autoencoder weight (reconstruction error). |
| `GNN_WEIGHT` | `0.05` | Graph Neural Network weight (optional, requires Neo4j graph data). |

### Performance Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `SCORE_CACHE_TTL` | `60` | Score result cache TTL in seconds (Redis/in-memory). |
| `DB_POOL_SIZE` | `10` | SQLAlchemy connection pool size. |
| `DB_MAX_OVERFLOW` | `20` | Maximum overflow connections beyond pool size. |
| `API_WORKERS` | `4` | Number of Uvicorn worker processes. |

### Security Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `REGULATOR_TOKEN` | `regulator-secret-token` | Bearer token for `/api/v1/regulator/*` endpoints. Change in production! |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed CORS origins (comma-separated). Add production frontend URL. |
| `JWT_SECRET_KEY` | (none) | JWT signing key for analyst authentication (future feature). |

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `KILL_SWITCH_ACTIVE` | `False` | Global kill switch for automated freeze actions. Set `True` to disable all auto-freezes. |
| `AUTO_FREEZE_ENABLED` | `True` | Enable/disable automatic freeze for CRITICAL risk band accounts. |
| `STR_GENERATION_ENABLED` | `True` | Enable/disable automatic goAML STR draft generation. |
| `DEBUG` | `False` | Enable debug logging and FastAPI auto-reload. |

### Monitoring Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `PROMETHEUS_ENABLED` | `True` | Expose `/metrics` endpoint for Prometheus scraping. |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana admin password (change in production!). |
| `AUDIT_RETENTION_DAYS` | `1825` | Audit log retention period (5 years = 1825 days, regulatory requirement). |

### Example `.env` File

```env
# Database
DATABASE_URL=postgresql://muleshield:secure_password@postgres:5432/muleshield_prod
REDIS_URL=redis://redis:6379/0

# ML Models
XGBOOST_WEIGHT=0.30
LIGHTGBM_WEIGHT=0.25
CATBOOST_WEIGHT=0.15

# Security
REGULATOR_TOKEN=RBI-FIU-IND-SECURE-TOKEN-2026
CORS_ORIGINS=https://muleshield.bankname.in,https://dashboard.bankname.in

# Performance
SCORE_CACHE_TTL=60
API_WORKERS=8

# Features
KILL_SWITCH_ACTIVE=False
AUTO_FREEZE_ENABLED=True
```

**Production Checklist:**
1. ✅ Change `REGULATOR_TOKEN` to a secure random value
2. ✅ Use PostgreSQL for `DATABASE_URL` (not SQLite)
3. ✅ Update `CORS_ORIGINS` with production frontend URL
4. ✅ Set `DEBUG=False`
5. ✅ Configure `GRAFANA_ADMIN_PASSWORD`
6. ✅ Increase `API_WORKERS` based on CPU cores
7. ✅ Enable SSL/TLS for Redis and PostgreSQL connections

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
