# Pokec hop-query benchmark — Postgres vs Memgraph

End-to-end recipe to run 1..5-hop reachability queries on the Pokec medium
dataset against both engines and compare timings.

## 0. Prerequisites

- Docker
- `uv` (https://docs.astral.sh/uv/)
- `psql` (Postgres client)
- `mgconsole` (Memgraph client — https://memgraph.com/docs/getting-started/install-memgraph/mgconsole)

## 1. Start Postgres 19

The provided `Dockerfile` builds a Postgres 19 image. Build it once and run it
on host port `5433` (which is what [load.sh](load.sh) expects):

```bash
docker build -t pg19-pokec .
docker run -d --name pg19-pokec -p 5433:5432 pg19-pokec
```

## 2. Start Memgraph

However you like — for example:

```bash
docker run -d --name memgraph -p 7687:7687 memgraph/memgraph
```

This exposes Bolt on `localhost:7687`.

## 3. Load the Pokec dataset into both engines

```bash
./load.sh
```

`load.sh` is the single entry point and does the following:

1. Waits for Postgres (`localhost:5433`) and Memgraph (`localhost:7687`) to be reachable.
2. Downloads the two prebuilt Pokec medium dumps if they aren't already next to the script:
   - https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.sql
   - https://s3.eu-west-1.amazonaws.com/deps.memgraph.io/dataset/pokec/benchmark/pokec_medium_import.cypher
3. Applies [schema.sql](schema.sql) and loads the SQL dump into Postgres in a
   single transaction, then runs [graph.sql](graph.sql) to create the
   `pokec` property graph.
4. Switches Memgraph to `IN_MEMORY_ANALYTICAL`, creates `INDEX ON :User` and
   `INDEX ON :User(id)`, streams the Cypher dump through `mgconsole`, then
   switches back to `IN_MEMORY_TRANSACTIONAL`.

If you'd rather create your own datasets, follow the schemas in
[schema.sql](schema.sql) (Postgres: `users(id, completion_percentage, gender,
age)` + `friendships(user_id, friend_id)`) and the corresponding Memgraph
shape `(:User {id, completion_percentage, gender, age})-[:FRIEND_OF]->(:User)`,
and drop them next to the script under the expected filenames — `load.sh`
will skip the download.

## 4. Install Python dependencies

From the repo root:

```bash
uv sync
```

This installs `gqlalchemy` (Memgraph) and `psycopg[binary]` (Postgres).

## 5. Run the benchmark

```bash
uv run python benchmarks/postgres_lpg_pokec_benchmark/benchmark.py
```

Sample knobs:

```bash
uv run python benchmarks/postgres_lpg_pokec_benchmark/benchmark.py \
    --start-id 40692 \
    --max-hops 5 \
    --iterations 5
```

Other flags:

- `--skip-postgres` / `--skip-memgraph` — benchmark only one engine
- `--pg-timeout-ms` — Postgres `statement_timeout` in ms (default 30000, `0` disables). Queries that exceed it are reported as `TIMEOUT` and the benchmark continues.

## 6. Configuration via env vars

| Variable  | Default                                            |
| --------- | -------------------------------------------------- |
| `PG_DSN`  | `postgresql://postgres@localhost:5433/postgres`    |
| `MG_HOST` | `localhost`                                        |
| `MG_PORT` | `7687`                                             |

`load.sh` also honors `PGHOST` / `PGPORT` / `PGUSER` / `PGDATABASE` and
`MG_HOST` / `MG_PORT`. If your Memgraph data lives under different labels,
edit `PERSON_LABEL` / `FRIEND_REL` near the top of [benchmark.py](benchmark.py).

## What the queries do

For each `N` in `1..max-hops`, both engines compute:

> The number of **distinct** users reachable in **exactly** `N` outbound
> `friend_of` hops from `--start-id`.

- Postgres — SQL/PGQ via `GRAPH_TABLE (pokec MATCH (v0 IS person WHERE v0.id = …)-[IS friend_of]->(v1)…->(vN) COLUMNS (vN.id AS end_id))`, wrapped in `SELECT count(DISTINCT end_id)`. This uses the property graph created by [graph.sql](graph.sql), so `./load.sh` must have run.
- Memgraph — `MATCH (a:User {id: $start})-[:FRIEND_OF *BFS N..N]->(b:User) RETURN count(DISTINCT b)` (BFS expansion, so paths can't revisit nodes).

Each query runs once as warmup (excluded), then `--iterations` timed runs.
The report prints min / avg / max latency per engine plus a speedup ratio.
