# Loading Apache Iceberg into Memgraph

Ingest data from [Apache Iceberg](https://iceberg.apache.org/) tables into Memgraph as a property graph.

- **Edition**: Community
- **Tested on**: Memgraph **v3.9**
- **Source backends**: PyIceberg, DuckDB (more coming: LOAD CSV/Parquet)

## What this example does

1. [`generate_iceberg.py`](./generate_iceberg.py) generates **1,000,000 users** and **5,000,000 transactions** with numpy and writes them to a local Iceberg warehouse via a PyIceberg `SqlCatalog` (SQLite metadata, local-filesystem warehouse). Zero infra. Sizes are configurable via `--users` / `--transactions`.
2. [`iceberg_to_memgraph.py`](./iceberg_to_memgraph.py) reads those Iceberg tables and writes them to Memgraph as `(:User)-[:SENT]->(:User)` using batched `UNWIND` queries via [gqlalchemy](https://github.com/memgraph/gqlalchemy) (Memgraph's Python client, built on `pymgclient`).

The reported elapsed time covers only the source → Memgraph ingestion (schema setup and graph reset are excluded), so the number reflects actual data movement.

## Why a local Iceberg catalog?

In production, Iceberg tables live in a data lake (S3 + AWS Glue / REST / Hive catalog). The local SQL catalog used here is a reproducible stand-in so the example runs end-to-end on a fresh clone — only the catalog config block in [`loaders/pyiceberg_loader.py`](./loaders/pyiceberg_loader.py) changes when you point at a real lake.

## Why gqlalchemy and not the official `neo4j` driver?

**Use [gqlalchemy](https://github.com/memgraph/gqlalchemy) when writing to Memgraph.** In our tests on this workload (1M users + 5M transactions, batched UNWIND), gqlalchemy delivered **at least a 2× ingestion throughput improvement** over the `neo4j` Python driver at the same `--workers` and `--batch-size`.

Why: gqlalchemy talks to Memgraph through [`pymgclient`](https://github.com/memgraph/pymgclient), a native C client built specifically for Memgraph's Bolt implementation. The `neo4j` driver is generic Bolt and adds per-call overhead (transactional bookmarking, server-routing checks, result-buffering) that bulk loads pay for on every batch but don't benefit from. For write-heavy ingestion via `UNWIND`, that overhead dominates.

Rule of thumb for this repo:
- **Writing to Memgraph** (ingest, ETL, bulk load): use gqlalchemy.
- **Read-mostly app code** where you want OGM ergonomics (Python classes ↔ nodes, query builder): also gqlalchemy.
- **Cross-vendor code that must run against Neo4j too**: use the `neo4j` driver.

## Run

### 1. Start Memgraph

```bash
docker compose up -d
```

Starts Memgraph 3.9 (Community) on `bolt://localhost:7687`. To inspect results visually, also run [Memgraph Lab](https://memgraph.com/docs/data-visualization).

### 2. Install dependencies

This example uses [uv](https://docs.astral.sh/uv/). Install it once if you don't have it (`curl -LsSf https://astral.sh/uv/install.sh | sh`), then sync the project env:

```bash
uv sync
```

### 3. Generate the Iceberg warehouse (once)

```bash
uv run python generate_iceberg.py
```

Expected output:

```
Generating 1,000,000 users...
Generating 5,000,000 transactions...
Writing Iceberg tables...

users:        1,000,000 rows
transactions: 5,000,000 rows
warehouse:    .../import/iceberg/warehouse
```

Generation takes ~10–20s and produces a few hundred MB of Parquet under `warehouse/`. Re-running drops and recreates the tables.

For a quick smoke test, scale down: `uv run python generate_iceberg.py --users 10000 --transactions 50000`.

### 4. Load Iceberg into Memgraph

Pick a source backend; optionally tune parallelism and batch size:

```bash
uv run python iceberg_to_memgraph.py --source pyiceberg                          # defaults
uv run python iceberg_to_memgraph.py --source duckdb --workers 8                 # 8 parallel writers
uv run python iceberg_to_memgraph.py --source pyiceberg --workers 8 --batch-size 50000
```

Expected output:

```
[pyiceberg, workers=1,  batch=10000, user-write=create] Ingested into Memgraph in 142.37s
[duckdb,    workers=8,  batch=10000, user-write=create] Ingested into Memgraph in  31.04s
[pyiceberg, workers=20, batch=25000, user-write=create] Ingested into Memgraph in  24.34s
```

Flags:

- `--workers N` — N parallel Bolt sessions writing to Memgraph. A single reader thread fills a bounded queue; N writer threads drain it. Memgraph is in analytical mode for the duration (set by `prepare_graph`), so concurrent writes don't conflict.
- `--batch-size N` — rows per UNWIND batch / Bolt round trip. Default 10000. Bigger batches amortize round-trip overhead but raise per-call memory; smaller batches expose more concurrency to workers but spend more time in network framing.

Tuning order: get `--batch-size` into the right ballpark first (1k–50k is typical), then crank `--workers` up to roughly the CPU count of the server. Comparing `pyiceberg` vs `duckdb` at equal `--workers` and `--batch-size` isolates the scan engine difference; the writer side is identical.

Exact time depends on hardware. The default sizes (1M nodes + 5M edges) typically ingest in 2–5 minutes single-threaded and noticeably faster with `--workers 4..16`.

## Verify

Connect via Memgraph Lab or `mgconsole` and run:

```cypher
MATCH (u:User)-[t:SENT]->(v:User)
RETURN u.name AS sender, v.name AS receiver, t.amount, t.ts
ORDER BY t.amount DESC
LIMIT 10;
```

You should see the top 10 transactions with sender/receiver names. To verify counts:

```cypher
MATCH (u:User) RETURN count(u);          // 1,000,000
MATCH ()-[t:SENT]->() RETURN count(t);   // 5,000,000
```

## Architecture

```
generate_iceberg.py  ──► warehouse/  (local Iceberg, 1M users + 5M txs)
                              │
                              ▼
              loaders/{pyiceberg,duckdb}_loader.py
                              │
                              ▼
                    iceberg_to_memgraph.py ──► Memgraph (Bolt)
```

[`iceberg_to_memgraph.py`](./iceberg_to_memgraph.py) is backend-agnostic — it talks to the `Loader` interface defined in [`loaders/base.py`](./loaders/base.py).

### Adding a new source backend

1. Implement `loaders/<your>.py` with `users()` and `transactions()` returning iterators of dict batches.
2. Register it in [`loaders/__init__.py`](./loaders/__init__.py) under `LOADERS`.
3. Run `python iceberg_to_memgraph.py --source <your>`.

### Pointing at a real Iceberg lake

Replace the `SqlCatalog(...)` block in [`loaders/pyiceberg_loader.py`](./loaders/pyiceberg_loader.py) with a configured catalog, e.g.:

```python
from pyiceberg.catalog import load_catalog

self.catalog = load_catalog("prod", **{
    "type": "rest",
    "uri":  "https://catalog.example.com",
    # ...credentials, warehouse, etc.
})
```

The rest of the loader and the entire writer stay the same.

## Files

| File | Purpose |
| --- | --- |
| [`generate_iceberg.py`](./generate_iceberg.py) | One-time: generate 1M users + 5M txs into local Iceberg tables |
| [`loaders/base.py`](./loaders/base.py) | Abstract `Loader` interface |
| [`loaders/pyiceberg_loader.py`](./loaders/pyiceberg_loader.py) | PyIceberg implementation |
| [`loaders/duckdb_loader.py`](./loaders/duckdb_loader.py) | DuckDB `iceberg_scan` implementation |
| [`iceberg_to_memgraph.py`](./iceberg_to_memgraph.py) | Backend-agnostic CLI loader |
| [`docker-compose.yml`](./docker-compose.yml) | Memgraph 3.9 (Community) |
| `warehouse/` | Generated by `generate_iceberg.py`, gitignored |
