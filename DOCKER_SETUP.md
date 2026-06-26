# MuleShield AI Docker Setup Guide

## Quick Start

### Prerequisites
- Docker Engine 20.10+ and Docker Compose V2
- At least 8GB RAM available for Docker
- 10GB free disk space
- DataSet.csv file (9,082 rows × 3,924 features)

### Step 1: Prepare Dataset
```bash
# Copy the dataset to the data directory
cp /path/to/DataSet.csv ./data/DataSet.csv

# Verify the file
ls -lh data/DataSet.csv
```

### Step 2: Configure Environment (Optional)
```bash
# Copy and edit environment variables if needed
cp .env.example .env
nano .env
```

### Step 3: Start the Stack
```bash
# Build and start all services
docker compose up --build

# Or run in detached mode
docker compose up --build -d
```

### Step 4: Access Services
After all services are healthy (takes ~2-3 minutes):

- **Dashboard**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **MLflow**: http://localhost:5000
- **Grafana**: http://localhost:3001 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Neo4j Browser**: http://localhost:7474 (neo4j/muleshield123)

## Service Architecture

### Core Services
1. **backend** - FastAPI scoring API (port 8000)
2. **frontend** - React dashboard via Nginx (port 3000)
3. **redis** - Feature store cache (port 6379)
4. **neo4j** - Transaction graph database (ports 7474, 7687)
5. **mlflow** - Model registry (port 5000)
6. **prometheus** - Metrics collection (port 9090)
7. **grafana** - Metrics visualization (port 3001)

### Init Container
- **train-models** - One-time model training (runs before backend)
  - Checks if models exist in `/app/artifacts/ensemble_metadata.json`
  - If not found, trains ensemble models using DataSet.csv
  - Skips training on subsequent restarts if models exist

## Service Dependencies

```
train-models → backend → frontend
              ↓
         redis, neo4j, mlflow
              ↓
         prometheus → grafana
```

## Health Checks

All services include health checks with automatic retry logic:

| Service | Endpoint | Interval | Timeout | Retries |
|---------|----------|----------|---------|---------|
| backend | GET /api/v1/health | 10s | 5s | 5 |
| frontend | GET /health | 10s | 5s | 3 |
| redis | redis-cli ping | 5s | 3s | 5 |
| neo4j | GET :7474 | 10s | 5s | 5 |
| mlflow | GET /health | 10s | 5s | 5 |
| prometheus | GET /-/healthy | 10s | 5s | 3 |
| grafana | GET /api/health | 10s | 5s | 3 |

## Volume Persistence

Data is persisted across container restarts in Docker volumes:

| Volume | Purpose | Path |
|--------|---------|------|
| model-artifacts | Trained models, scaler, imputer | /app/artifacts |
| sqlite-data | Audit logs, scores, actions | /app/db |
| redis-data | Cached scores (optional) | /data |
| neo4j-data | Transaction graph | /data |
| mlflow-data | Experiment tracking | /mlflow |
| prometheus-data | Time-series metrics | /prometheus |
| grafana-data | Dashboards, settings | /var/lib/grafana |

## Common Operations

### View Logs
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f backend

# Tail last 100 lines
docker compose logs --tail=100 backend
```

### Check Service Status
```bash
# List all services
docker compose ps

# Check health
docker compose ps --format json | jq -r '.[] | "\(.Name): \(.Health)"'
```

### Restart a Service
```bash
# Restart backend only
docker compose restart backend

# Rebuild and restart
docker compose up --build --force-recreate backend
```

### Stop Services
```bash
# Stop all services (preserves data)
docker compose stop

# Stop and remove containers (preserves volumes)
docker compose down

# Stop and remove everything including volumes (CAUTION: deletes data)
docker compose down -v
```

### Manual Model Training
```bash
# Retrain models manually
docker compose exec backend python scripts/train.py \
  --data /data/DataSet.csv \
  --artifacts /app/artifacts \
  --mlflow-uri http://mlflow:5000

# Then restart backend to load new models
docker compose restart backend
```

### Access Container Shell
```bash
# Backend shell
docker compose exec backend bash

# Run Python REPL with app context
docker compose exec backend python

# Neo4j Cypher shell
docker compose exec neo4j cypher-shell -u neo4j -p muleshield123
```

### Database Operations
```bash
# Backup SQLite database
docker compose exec backend sqlite3 /app/db/muleshield.db .dump > backup.sql

# Restore SQLite database
cat backup.sql | docker compose exec -T backend sqlite3 /app/db/muleshield.db

# View audit log
docker compose exec backend sqlite3 /app/db/muleshield.db \
  "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT 10;"
```

## Troubleshooting

### Backend Fails to Start
```bash
# Check if models were trained
docker compose exec backend ls -la /app/artifacts/

# Check logs for training errors
docker compose logs train-models

# Manually trigger training
docker compose run --rm train-models python scripts/train.py --data /data/DataSet.csv
```

### Frontend Can't Connect to Backend
```bash
# Verify backend is healthy
curl http://localhost:8000/api/v1/health

# Check CORS settings in backend
docker compose exec backend env | grep CORS

# Rebuild frontend with correct API URL
docker compose up --build frontend
```

### Redis Connection Errors
```bash
# Test Redis connectivity
docker compose exec backend python -c "import redis; r=redis.from_url('redis://redis:6379/0'); print(r.ping())"

# Check Redis memory usage
docker compose exec redis redis-cli INFO memory
```

### Neo4j Connection Issues
```bash
# Test Neo4j connectivity
docker compose exec neo4j cypher-shell -u neo4j -p muleshield123 "RETURN 1;"

# Check Neo4j logs
docker compose logs neo4j | tail -50
```

### Out of Memory
```bash
# Check container resource usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
# Or limit individual services in docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

### Port Conflicts
If ports are already in use, edit docker-compose.yml:
```yaml
# Change port mapping (host:container)
ports:
  - "8001:8000"  # Use 8001 instead of 8000
```

## Production Deployment

### Security Checklist
- [ ] Change `REGULATOR_TOKEN` in environment
- [ ] Change Neo4j password (`NEO4J_AUTH`)
- [ ] Change Grafana admin password (`GF_SECURITY_ADMIN_PASSWORD`)
- [ ] Use PostgreSQL instead of SQLite for `DATABASE_URL`
- [ ] Enable SSL/TLS for all external connections
- [ ] Configure firewall rules to restrict port access
- [ ] Set `DEBUG=False`
- [ ] Use Docker secrets for sensitive environment variables
- [ ] Enable audit log encryption
- [ ] Configure backup automation for all volumes

### Performance Tuning
```yaml
# Add to backend service in docker-compose.yml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 8G
    reservations:
      cpus: '2'
      memory: 4G
  replicas: 2  # For load balancing (requires swarm mode)
```

### Monitoring Setup
1. Configure Prometheus retention: `--storage.tsdb.retention.time=90d`
2. Set up Grafana alerts with notification channels (email, Slack)
3. Enable Neo4j metrics plugin
4. Add Redis exporter for cache metrics
5. Configure log aggregation (ELK stack, Loki)

## Network Architecture

All services communicate via the `muleshield-network` bridge network:
- Subnet: 172.28.0.0/16
- Internal DNS resolution by service name
- Frontend → backend via `http://backend:8000`
- Backend → redis via `redis://redis:6379`
- Backend → neo4j via `bolt://neo4j:7687`
- Prometheus → backend via `http://backend:8000/metrics`

## Development Workflow

### Local Development with Hot Reload
```yaml
# Add to docker-compose.override.yml (not tracked in git)
services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./backend:/app  # Bind mount for hot reload
  
  frontend:
    command: npm run start
    ports:
      - "5173:5173"  # Vite dev server
```

### Run Tests in Container
```bash
# Backend tests
docker compose exec backend pytest tests/ -v

# Frontend tests
docker compose exec frontend npm test
```

## Additional Resources

- **FastAPI Docs**: http://localhost:8000/docs
- **MLflow Experiments**: http://localhost:5000/#/experiments
- **Prometheus Targets**: http://localhost:9090/targets
- **Grafana Dashboard**: http://localhost:3001/d/muleshield-main

## Support

For issues or questions:
1. Check logs: `docker compose logs <service-name>`
2. Verify health: `docker compose ps`
3. Review this guide's troubleshooting section
4. Consult project README.md
