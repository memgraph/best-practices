# Power BI <-> Memgraph Integration

Three approaches to visualize Memgraph graph data in Microsoft Power BI.

- **Power BI Desktop** (Windows) — see [DESKTOP.md](DESKTOP.md)
- **Power BI Service** (web, any OS) — see [SERVICE.md](SERVICE.md)

## Prerequisites

- Docker (for Memgraph)
- Python 3.10+

## Quick Start

```bash
# 1. Start Memgraph
docker compose up -d memgraph

# 2. Install Python dependencies
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Seed sample data (5 persons, 3 companies, 3 products, 16 relationships)
python seed.py
```

## Approaches

| Approach | Description | Desktop | Service | Cost |
|----------|-------------|---------|---------|------|
| Python Script | Query Memgraph directly from Power BI's Python data source | Yes | No | Free |
| REST API | FastAPI middleware exposes Memgraph data as JSON endpoints | Yes | Yes (via Dataflow) | Free |
| ODBC | Third-party driver translates SQL to Cypher over Bolt | Yes | Yes (via Gateway) | Paid |

## REST API

The REST API (Approach 2) is shared across Desktop and Service. Start it before connecting from either.

```bash
# Option A: Run locally
uvicorn rest_api:app --host 0.0.0.0 --port 8000

# Option B: Run everything with Docker Compose (Memgraph + API)
docker compose up -d

# Verify
curl http://localhost:8000/person-purchases
```

### Available endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/nodes` | GET | All nodes as flat rows |
| `/edges` | GET | All edges as flat rows |
| `/person-purchases` | GET | Persons with purchases (good for charts) |
| `/company-employees` | GET | Companies with employee details |
| `/query` | POST | Run arbitrary Cypher, returns list of dicts |

## Files

```
powerbi_integration/
├── docker-compose.yml          # Memgraph + FastAPI service
├── Dockerfile                  # FastAPI container
├── requirements.txt            # Python deps
├── seed.py                     # Seed sample data into Memgraph
├── rest_api.py                 # FastAPI service
├── direct_query.py             # Power BI Desktop Python script
├── push_to_powerbi.py          # Push data to Power BI Service datasets
├── DESKTOP.md                  # Guide for Power BI Desktop (Windows)
└── SERVICE.md                  # Guide for Power BI Service (web, any OS)
```
