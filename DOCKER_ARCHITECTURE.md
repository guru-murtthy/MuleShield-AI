# MuleShield AI Docker Architecture

## Service Topology

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Stack                          │
│                     Network: muleshield-network                      │
│                        (172.28.0.0/16)                              │
└─────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ INIT PHASE (Runs Once)                                                │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─────────────────────────────────────────┐                         │
│  │   train-models (Init Container)         │                         │
│  │   ────────────────────────────────      │                         │
│  │   • Checks: artifacts/ensemble.json     │                         │
│  │   • Trains models if not found          │                         │
│  │   • Reads: /data/DataSet.csv            │                         │
│  │   • Writes: /app/artifacts/*            │                         │
│  │   • Logs to MLflow                      │                         │
│  │   • Exit: success (unblocks backend)    │                         │
│  └─────────────────────────────────────────┘                         │
│                      │                                                 │
│                      │ depends_on:                                     │
│                      ▼                                                 │
│            ┌──────────────────┐                                       │
│            │   mlflow:5000    │                                       │
│            └──────────────────┘                                       │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ USER INTERFACE LAYER                                                  │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌────────────────────────────────────────────────────┐              │
│  │  frontend (Nginx) :3000                            │              │
│  │  ──────────────────────────                        │              │
│  │  • React 18 + TypeScript + Vite                    │              │
│  │  • Nginx with SPA routing                          │              │
│  │  • Gzip compression                                │              │
│  │  • Security headers                                │              │
│  │  • API proxy to backend:8000                       │              │
│  │  • Healthcheck: GET /health                        │              │
│  └────────────────────────────────────────────────────┘              │
│                           │                                            │
│                           │ HTTP REST API                              │
│                           ▼                                            │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                                     │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌────────────────────────────────────────────────────┐              │
│  │  backend (FastAPI) :8000                           │              │
│  │  ───────────────────────                           │              │
│  │  • 4 Uvicorn workers                               │              │
│  │  • Endpoints: /score, /health, /alerts,            │              │
│  │    /action, /regulator, /audit, /kill-switch       │              │
│  │  • Ensemble model inference                        │              │
│  │  • SHAP explainability                             │              │
│  │  • Prometheus metrics: /metrics                    │              │
│  │  • Healthcheck: GET /api/v1/health                 │              │
│  └────────────────────────────────────────────────────┘              │
│         │              │              │              │                 │
│         ▼              ▼              ▼              ▼                 │
│    ┌────────┐    ┌────────┐    ┌──────────┐   ┌─────────┐           │
│    │ Redis  │    │ SQLite │    │  Neo4j   │   │ MLflow  │           │
│    │ :6379  │    │  /db   │    │:7474/7687│   │  :5000  │           │
│    └────────┘    └────────┘    └──────────┘   └─────────┘           │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ DATA LAYER                                                            │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │  redis:6379      │  │  neo4j:7474/7687 │  │  mlflow:5000     │   │
│  │  ─────────       │  │  ────────────    │  │  ────────        │   │
│  │  • Feature cache │  │  • Graph DB      │  │  • Model registry│   │
│  │  • 512MB memory  │  │  • 1GB heap      │  │  • Artifacts     │   │
│  │  • LRU eviction  │  │  • APOC plugin   │  │  • Experiments   │   │
│  │  • AOF persist   │  │  • Auth: neo4j/  │  │  • SQLite store  │   │
│  │  • 60s TTL       │  │    muleshield123 │  │  • File artifacts│   │
│  │  • Healthcheck:  │  │  • Healthcheck:  │  │  • Healthcheck:  │   │
│  │    redis-cli ping│  │    HTTP :7474    │  │    GET /health   │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                                                                        │
│  ┌────────────────────────────────────────────────────┐              │
│  │  SQLite (volume: sqlite-data)                      │              │
│  │  ───────────────────────────                       │              │
│  │  • Database: muleshield.db                         │              │
│  │  • Tables: ScoreRecord, AccountAction, AuditLog    │              │
│  │  • Audit chain with SHA-256 hashing                │              │
│  │  • Append-only audit logs                          │              │
│  └────────────────────────────────────────────────────┘              │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ MONITORING LAYER                                                      │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌──────────────────────────────────────┐                            │
│  │  grafana:3001                        │                            │
│  │  ────────────                        │                            │
│  │  • Admin: admin/admin                │                            │
│  │  • Auto-provisioned Prometheus DS    │                            │
│  │  • Pre-configured dashboard          │                            │
│  │  • Panels: Request rate, latency,    │                            │
│  │    alerts, freeze actions, AUC-ROC   │                            │
│  │  • Healthcheck: GET /api/health      │                            │
│  └──────────────────────────────────────┘                            │
│                    │                                                   │
│                    │ queries                                           │
│                    ▼                                                   │
│  ┌──────────────────────────────────────┐                            │
│  │  prometheus:9090                     │                            │
│  │  ───────────────                     │                            │
│  │  • Scrapes: backend:8000/metrics     │                            │
│  │  • Interval: 15s                     │                            │
│  │  • Retention: 30 days                │                            │
│  │  • Metrics: requests, latency,       │                            │
│  │    alerts, freeze_actions            │                            │
│  │  • Healthcheck: GET /-/healthy       │                            │
│  └──────────────────────────────────────┘                            │
│                    ▲                                                   │
│                    │ scrapes                                           │
│                    │                                                   │
│              (backend /metrics)                                        │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ STORAGE VOLUMES (Persistent)                                         │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  • model-artifacts    → /app/artifacts (models, scaler, imputer)     │
│  • sqlite-data        → /app/db (audit logs, scores, actions)        │
│  • redis-data         → /data (cache persistence - optional)         │
│  • neo4j-data         → /data (transaction graph)                    │
│  • neo4j-logs         → /logs (Neo4j logs)                           │
│  • neo4j-import       → /var/lib/neo4j/import (bulk import)          │
│  • neo4j-plugins      → /plugins (APOC, etc.)                        │
│  • mlflow-data        → /mlflow (experiments, artifacts)             │
│  • prometheus-data    → /prometheus (time-series metrics)            │
│  • grafana-data       → /var/lib/grafana (dashboards, settings)      │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────────────┐
│ EXTERNAL VOLUMES (Bind Mounts)                                       │
├───────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  • ./data:/data (ro)                → DataSet.csv (read-only)        │
│  • ./backend:/app                   → Backend code (dev mode)        │
│  • ./monitoring/prometheus:/etc/... → Prometheus config              │
│  • ./monitoring/grafana:/etc/...    → Grafana provisioning           │
│                                                                        │
└───────────────────────────────────────────────────────────────────────┘
```

## Service Startup Sequence

```
1. Docker creates network: muleshield-network (172.28.0.0/16)
   │
   ▼
2. Docker creates volumes: model-artifacts, sqlite-data, redis-data, etc.
   │
   ▼
3. Start data layer services (no dependencies):
   ├─ redis:6379          [Wait for healthcheck: redis-cli ping]
   ├─ neo4j:7474/7687     [Wait for healthcheck: HTTP :7474]
   └─ mlflow:5000         [Wait for healthcheck: GET /health]
   │
   ▼
4. Start init container: train-models
   │  depends_on: mlflow (service_healthy)
   │  • Check: /app/artifacts/ensemble_metadata.json exists?
   │  • If NO:  Train models → Save to artifacts → Exit 0
   │  • If YES: Skip training → Exit 0
   │
   ▼
5. Start application layer: backend:8000
   │  depends_on:
   │    - redis (service_healthy)
   │    - neo4j (service_healthy)
   │    - mlflow (service_healthy)
   │    - train-models (service_completed_successfully)
   │  [Wait for healthcheck: GET /api/v1/health]
   │
   ▼
6. Start user interface: frontend:3000
   │  depends_on: backend (service_healthy)
   │  [Wait for healthcheck: GET /health]
   │
   ▼
7. Start monitoring layer:
   ├─ prometheus:9090 [depends_on: backend (service_healthy)]
   │                  [Wait for healthcheck: GET /-/healthy]
   └─ grafana:3001    [depends_on: prometheus (service_healthy)]
                      [Wait for healthcheck: GET /api/health]
   │
   ▼
8. All services healthy → Stack ready!
   Total startup time: ~90-120 seconds (first run with training: 5-10 minutes)
```

## Data Flow

### Scoring Request Flow
```
User → Frontend:3000
   │
   └─→ POST /api/v1/score
        │
        └─→ Backend:8000
             │
             ├─→ Redis:6379 (check cache)
             │   └─→ Cache hit? Return cached score
             │
             ├─→ Load models from /app/artifacts/
             │
             ├─→ Run ensemble prediction
             │
             ├─→ Compute SHAP values
             │
             ├─→ Assign risk band
             │
             ├─→ Detect patterns
             │
             ├─→ Generate narrative
             │
             ├─→ Save to SQLite (/app/db/muleshield.db)
             │
             ├─→ Cache in Redis (60s TTL)
             │
             ├─→ Log to AuditLog (SHA-256 chain)
             │
             └─→ Return ScoreResponse → Frontend
```

### Model Training Flow
```
train-models (Init Container)
   │
   ├─→ Read: /data/DataSet.csv (9,082 rows × 3,924 features)
   │
   ├─→ Preprocess:
   │   ├─ Drop columns >70% missing
   │   ├─ Impute median on train split
   │   ├─ StandardScaler normalization
   │   └─ Stratified split 80/20
   │
   ├─→ Train ensemble:
   │   ├─ XGBoost (weight 0.30)
   │   ├─ LightGBM (weight 0.25)
   │   ├─ CatBoost (weight 0.15)
   │   ├─ Isolation Forest (weight 0.15)
   │   ├─ Autoencoder (weight 0.10)
   │   └─ GNN (weight 0.05)
   │
   ├─→ Evaluate:
   │   ├─ AUC-ROC
   │   ├─ AUC-PR
   │   ├─ F1-score
   │   └─ Confusion matrix
   │
   ├─→ Save artifacts to /app/artifacts/:
   │   ├─ ensemble_metadata.json
   │   ├─ xgboost_model.pkl
   │   ├─ lightgbm_model.pkl
   │   ├─ catboost_model.cbm
   │   ├─ isolation_forest.pkl
   │   ├─ autoencoder.h5
   │   ├─ gnn_model.pth
   │   ├─ scaler.pkl
   │   ├─ imputer.pkl
   │   └─ eval_metrics.json
   │
   ├─→ Log to MLflow:5000
   │   ├─ Experiment: muleshield-ensemble
   │   ├─ Metrics: AUC-ROC, AUC-PR, F1
   │   ├─ Params: weights, thresholds, seed
   │   ├─ Tags: timestamp, dataset_checksum
   │   └─ Artifacts: models, scalers
   │
   └─→ Exit 0 (unblocks backend startup)
```

### Monitoring Flow
```
Backend:8000
   │
   ├─→ Generate metrics:
   │   ├─ muleshield_requests_total
   │   ├─ muleshield_score_latency_seconds
   │   ├─ muleshield_alerts_active
   │   ├─ muleshield_freeze_actions_total
   │   ├─ muleshield_cache_hit_rate
   │   ├─ muleshield_model_auc_roc
   │   └─ muleshield_detection_patterns_total
   │
   ├─→ Expose at /metrics (Prometheus format)
   │
   └─→ Prometheus:9090 scrapes every 15s
        │
        ├─→ Store in time-series DB (/prometheus)
        │
        └─→ Grafana:3001 queries Prometheus
             │
             └─→ Display in dashboard:
                 ├─ Request rate panel
                 ├─ Latency percentiles (p50, p95, p99)
                 ├─ Active alerts by risk band
                 ├─ Freeze actions timeline
                 ├─ Model AUC-ROC gauge
                 ├─ Detection patterns pie chart
                 └─ Cache hit rate gauge
```

## Port Mappings

| Service     | Internal Port | Host Port | Purpose                  |
|-------------|---------------|-----------|--------------------------|
| frontend    | 80            | 3000      | React dashboard (Nginx)  |
| backend     | 8000          | 8000      | FastAPI REST API         |
| redis       | 6379          | 6379      | Redis cache              |
| neo4j       | 7474          | 7474      | Neo4j HTTP browser       |
| neo4j       | 7687          | 7687      | Neo4j Bolt protocol      |
| mlflow      | 5000          | 5000      | MLflow UI                |
| prometheus  | 9090          | 9090      | Prometheus UI            |
| grafana     | 3000          | 3001      | Grafana dashboards       |

## Environment Variables

All services inherit environment variables from docker-compose.yml or .env file.

Key configurations:
- **Backend**: Model weights, cache TTL, database URL, API workers
- **Redis**: Memory limit, eviction policy
- **Neo4j**: Auth credentials, memory settings, APOC plugins
- **MLflow**: Tracking URI, backend store, artifact root
- **Prometheus**: Retention, scrape interval
- **Grafana**: Admin credentials, anonymous access

## Resource Requirements

### Minimum (Development)
- **RAM**: 8GB
- **CPU**: 4 cores
- **Disk**: 10GB

### Recommended (Production)
- **RAM**: 16GB
- **CPU**: 8 cores
- **Disk**: 50GB (with 30-day metrics retention)

### Per-Service Estimates
- **backend**: 2GB RAM, 2 CPU
- **frontend**: 128MB RAM, 0.5 CPU
- **redis**: 512MB RAM, 0.5 CPU
- **neo4j**: 2GB RAM, 1 CPU
- **mlflow**: 512MB RAM, 0.5 CPU
- **prometheus**: 1GB RAM, 1 CPU
- **grafana**: 256MB RAM, 0.5 CPU
- **train-models**: 4GB RAM, 2 CPU (during training only)

## Security Model

### Network Isolation
- All services communicate via internal bridge network (172.28.0.0/16)
- Only exposed ports are accessible from host
- No services directly accessible from external networks (unless port-forwarded)

### Authentication
- **Neo4j**: Username/password (neo4j/muleshield123)
- **Grafana**: Admin credentials (admin/admin)
- **Backend Regulator API**: Token-based auth (X-Regulator-Token header)
- **Redis**: No auth (internal network only)
- **MLflow**: No auth (internal network only)

### Data Protection
- **DataSet.csv**: Mounted read-only (ro)
- **Audit logs**: Append-only with SHA-256 chain
- **Volumes**: Persisted with proper permissions
- **Secrets**: Should use Docker secrets in production (not env vars)

### Security Headers (Frontend)
- X-Frame-Options: SAMEORIGIN
- X-Content-Type-Options: nosniff
- X-XSS-Protection: 1; mode=block

## Troubleshooting Quick Reference

| Issue | Command | Expected Output |
|-------|---------|-----------------|
| Check all services | `docker compose ps` | All status: Up (healthy) |
| View logs | `docker compose logs -f <service>` | Service logs |
| Test backend health | `curl http://localhost:8000/api/v1/health` | `{"status": "ok"}` |
| Test Redis | `docker compose exec redis redis-cli ping` | `PONG` |
| Test Neo4j | `curl http://localhost:7474` | HTML response |
| Check models exist | `docker compose exec backend ls /app/artifacts/` | `ensemble_metadata.json` |
| Restart service | `docker compose restart <service>` | Service restarted |
| Rebuild service | `docker compose up --build <service>` | Service rebuilt |
| Stop all | `docker compose down` | All containers stopped |
| Clean volumes | `docker compose down -v` | All data deleted |

## Next Steps

After services are running:

1. **Verify Training**: Check MLflow UI (http://localhost:5000) for training runs
2. **Test API**: Visit FastAPI docs (http://localhost:8000/docs) and try POST /api/v1/score
3. **View Dashboard**: Open frontend (http://localhost:3000) and verify alert queue
4. **Check Monitoring**: View Grafana dashboard (http://localhost:3001) for metrics
5. **Explore Graph**: Open Neo4j browser (http://localhost:7474) and query graph
