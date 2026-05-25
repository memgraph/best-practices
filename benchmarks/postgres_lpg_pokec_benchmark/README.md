# Pokec hop-query benchmark — Postgres vs Memgraph

End-to-end recipe to run 1..5-hop reachability queries on the Pokec medium
dataset against both engines and compare timings.

## 0. Prerequisites

- Docker
- `uv` (https://docs.astral.sh/uv/)

## 1. Start Postgres 19

The provided `Dockerfile` builds a Postgres 19 image. Build it once and run it
on host port `5433` (which is what [load.sh](load.sh) expects):

```bash
docker build -t pg19-pokec pokec_graph_example
docker run -d --name pg19-pokec -p 5433:5432 pg19-pokec
```

Wait a couple of seconds for the cluster to come up, then sanity-check:

```bash
psql -h localhost -p 5433 -U postgres -c '\l'
```

## 2. Load the Pokec dataset into Postgres

The benchmark expects two tables — `users(id, completion_percentage, gender, age)`
and `friendships(user_id, friend_id)` — populated with Pokec data. You can
either build your own dump matching that schema (see [schema.sql](schema.sql))
or use the prebuilt Pokec medium dump we host on S3:

- Postgres dump (`INSERT` statements, ~123 MB):
  https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.sql

From the repo root:

```bash
./pokec_graph_example/load.sh
```

`load.sh` downloads the dump on first run, applies [schema.sql](schema.sql),
loads the rows in a single transaction, then runs the property-graph setup
from [graph.sql](graph.sql).

## 3. Start Memgraph

From the repo root (uses [docker-compose.yml](../docker-compose.yml)):

```bash
docker compose up -d memgraph
```

This exposes Bolt on `localhost:7687`.

## 4. Install Python dependencies

From the repo root:

```bash
uv sync
```

This installs `gqlalchemy` (Memgraph) and `psycopg[binary]` (Postgres).

## 5. Load the Pokec dataset into Memgraph

Memgraph expects `(:User {id, completion_percentage, gender, age})-[:FRIEND_OF]->(:User)`.
You have two options.

**Option A — load directly from a Cypher dump.** Use your own dump that
follows the schema above, or grab our prebuilt one:

- Memgraph Cypher dump:
  https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.cypher

Before importing, create the indexes (required for fast lookups during the
edge-creation phase):

```cypher
CREATE INDEX ON :User;
CREATE INDEX ON :User(id);
```

Then load the file with `mgconsole` or any Bolt client.

**Option B — copy from Postgres.** Mirror `users` + `friendships` from the
already-loaded Postgres into Memgraph (first time only):

```bash
uv run python pokec_graph_example/benchmark.py --load-memgraph
```

The loader switches Memgraph to `IN_MEMORY_ANALYTICAL` for the bulk insert,
creates the `:User` / `:User(id)` indexes, then switches back to
`IN_MEMORY_TRANSACTIONAL`.

## 6. Run the benchmark

```bash
uv run python pokec_graph_example/benchmark.py
```

Sample knobs:

```bash
uv run python pokec_graph_example/benchmark.py \
    --start-id 40692 \
    --max-hops 5 \
    --iterations 5
```

Other flags:

- `--skip-postgres` / `--skip-memgraph` — benchmark only one engine
- `--load-memgraph` — re-load Memgraph from Postgres (drops the graph first)
- `--pg-timeout-ms` — Postgres `statement_timeout` in ms (default 30000, `0` disables). Queries that exceed it are reported as `TIMEOUT` and the benchmark continues.

## 7. Configuration via env vars

| Variable  | Default                                            |
| --------- | -------------------------------------------------- |
| `PG_DSN`  | `postgresql://postgres@localhost:5433/postgres`    |
| `MG_HOST` | `localhost`                                        |
| `MG_PORT` | `7687`                                             |

If your Memgraph already has the data under different labels, edit
`PERSON_LABEL` / `FRIEND_REL` near the top of [benchmark.py](benchmark.py).

## What the queries do

For each `N` in `1..max-hops`, both engines compute:

> The number of **distinct** users reachable in **exactly** `N` outbound
> `friend_of` hops from `--start-id`.

- Postgres — SQL/PGQ via `GRAPH_TABLE (pokec MATCH (v0 IS person WHERE v0.id = …)-[IS friend_of]->(v1)…->(vN) COLUMNS (vN.id AS end_id))`, wrapped in `SELECT count(DISTINCT end_id)`. This uses the property graph created by [graph.sql](graph.sql), so `./load.sh` must have run.
- Memgraph — `MATCH (a:User {id: $start})-[:FRIEND_OF *BFS N..N]->(b:User) RETURN count(DISTINCT b)` (BFS expansion, so paths can't revisit nodes).

Each query runs once as warmup (excluded), then `--iterations` timed runs.
The report prints min / avg / max latency per engine plus a speedup ratio.
