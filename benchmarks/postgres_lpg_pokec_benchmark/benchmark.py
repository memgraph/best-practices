"""
Benchmark 1..5-hop reachability on the Pokec dataset against Postgres and Memgraph.

Postgres: chained self-joins on the `friendships` table via psycopg (v3).
Memgraph: variable-length pattern via gqlalchemy.

Both queries count the distinct users reachable in exactly N hops from a starting user.

Usage:
    ./load.sh                            # one-time: load both engines
    uv run python benchmark.py
    uv run python benchmark.py --start-id 40692 --iterations 5 --max-hops 5
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from contextlib import contextmanager
from typing import Iterable

import psycopg
from gqlalchemy import Memgraph


PG_DSN = os.environ.get(
    "PG_DSN",
    "postgresql://postgres@localhost:5433/postgres",
)
MG_HOST = os.environ.get("MG_HOST", "localhost")
MG_PORT = int(os.environ.get("MG_PORT", "7687"))

PERSON_LABEL = "User"
FRIEND_REL = "FRIEND_OF"
PG_GRAPH_NAME = "pokec"

# Postgres SQL/PGQ — hardcoded for hops 1..5. {start_id} is replaced with int.
PG_HOP_QUERIES: dict[int, str] = {
    1: """\
SELECT count(DISTINCT end_id) AS reachable
FROM GRAPH_TABLE (pokec
    MATCH (v0 IS person WHERE v0.id = {start_id})
          -[IS friend_of]->(v1 IS person)
    COLUMNS (v1.id AS end_id)
);""",
    2: """\
SELECT count(DISTINCT end_id) AS reachable
FROM GRAPH_TABLE (pokec
    MATCH (v0 IS person WHERE v0.id = {start_id})
          -[IS friend_of]->(v1 IS person)
          -[IS friend_of]->(v2 IS person)
    COLUMNS (v2.id AS end_id)
);""",
    3: """\
SELECT count(DISTINCT end_id) AS reachable
FROM GRAPH_TABLE (pokec
    MATCH (v0 IS person WHERE v0.id = {start_id})
          -[IS friend_of]->(v1 IS person)
          -[IS friend_of]->(v2 IS person)
          -[IS friend_of]->(v3 IS person)
    COLUMNS (v3.id AS end_id)
);""",
    4: """\
SELECT count(DISTINCT end_id) AS reachable
FROM GRAPH_TABLE (pokec
    MATCH (v0 IS person WHERE v0.id = {start_id})
          -[IS friend_of]->(v1 IS person)
          -[IS friend_of]->(v2 IS person)
          -[IS friend_of]->(v3 IS person)
          -[IS friend_of]->(v4 IS person)
    COLUMNS (v4.id AS end_id)
);""",
    5: """\
SELECT count(DISTINCT end_id) AS reachable
FROM GRAPH_TABLE (pokec
    MATCH (v0 IS person WHERE v0.id = {start_id})
          -[IS friend_of]->(v1 IS person)
          -[IS friend_of]->(v2 IS person)
          -[IS friend_of]->(v3 IS person)
          -[IS friend_of]->(v4 IS person)
          -[IS friend_of]->(v5 IS person)
    COLUMNS (v5.id AS end_id)
);""",
}

# Memgraph Cypher — hardcoded for hops 1..5. Uses Memgraph's *BFS expansion,
# which finds shortest paths of the given length (BFS semantics — no repeated
# nodes within a path). Bound with parameter $start.
MG_HOP_QUERIES: dict[int, str] = {
    1: """\
MATCH (a:User {id: $start})-[:FRIEND_OF *BFS 1..1]->(b:User)
RETURN count(DISTINCT b) AS reachable;""",
    2: """\
MATCH (a:User {id: $start})-[:FRIEND_OF *BFS 2..2]->(b:User)
RETURN count(DISTINCT b) AS reachable;""",
    3: """\
MATCH (a:User {id: $start})-[:FRIEND_OF *BFS 3..3]->(b:User)
RETURN count(DISTINCT b) AS reachable;""",
    4: """\
MATCH (a:User {id: $start})-[:FRIEND_OF *BFS 4..4]->(b:User)
RETURN count(DISTINCT b) AS reachable;""",
    5: """\
MATCH (a:User {id: $start})-[:FRIEND_OF *BFS 5..5]->(b:User)
RETURN count(DISTINCT b) AS reachable;""",
}

MAX_SUPPORTED_HOPS = min(len(PG_HOP_QUERIES), len(MG_HOP_QUERIES))


def pg_hop_query(n: int, start_id: int) -> str:
    return PG_HOP_QUERIES[n].format(start_id=start_id)


def mg_hop_query(n: int) -> str:
    return MG_HOP_QUERIES[n]


@contextmanager
def timed() -> Iterable[list]:
    container: list[float] = []
    t0 = time.perf_counter()
    try:
        yield container
    finally:
        container.append(time.perf_counter() - t0)


def benchmark_postgres(
    start_id: int, max_hops: int, iterations: int, timeout_ms: int = 30_000
) -> dict:
    results: dict[int, dict] = {}
    with psycopg.connect(PG_DSN, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SET work_mem = '1GB';")
            print(">>> postgres work_mem = 1GB")
            if timeout_ms > 0:
                cur.execute(f"SET statement_timeout = {timeout_ms};")
                print(f">>> postgres statement_timeout = {timeout_ms} ms")
            for n in range(1, max_hops + 1):
                query = pg_hop_query(n, start_id)
                print(f"\n--- postgres {n}-hop ---\n{query}")
                try:
                    # Warmup (excluded from stats).
                    cur.execute(query)
                    reachable = cur.fetchone()[0]
                except psycopg.errors.QueryCanceled:
                    print(f"    timed out after {timeout_ms} ms — skipping {n}-hop")
                    results[n] = {"reachable": None, "times": [], "timed_out": True}
                    continue

                times: list[float] = []
                timed_out = False
                for _ in range(iterations):
                    try:
                        with timed() as t:
                            cur.execute(query)
                            cur.fetchone()
                        times.extend(t)
                    except psycopg.errors.QueryCanceled:
                        print(f"    iteration timed out after {timeout_ms} ms")
                        timed_out = True
                        break
                results[n] = {
                    "reachable": reachable,
                    "times": times,
                    "timed_out": timed_out,
                }
    return results


def benchmark_memgraph(start_id: int, max_hops: int, iterations: int) -> dict:
    db = Memgraph(host=MG_HOST, port=MG_PORT)
    results: dict[int, dict] = {}
    for n in range(1, max_hops + 1):
        query = mg_hop_query(n)
        params = {"start": start_id}
        print(f"\n--- memgraph {n}-hop ---\n{query}\nparams={params}")
        # Warmup.
        reachable = next(iter(db.execute_and_fetch(query, params)))["reachable"]

        times: list[float] = []
        for _ in range(iterations):
            with timed() as t:
                next(iter(db.execute_and_fetch(query, params)))
            times.extend(t)
        results[n] = {"reachable": reachable, "times": times}
    return results


def fmt_time(times: list[float], timed_out: bool = False) -> str:
    if not times:
        return "TIMEOUT" if timed_out else "n/a"
    avg_ms = statistics.mean(times) * 1000
    if avg_ms < 1000:
        return f"{avg_ms:,.2f} ms"
    return f"{avg_ms / 1000:,.2f} s"


def fmt(times: list[float], timed_out: bool = False) -> str:
    """Verbose (min/avg/max) formatter, retained for the single-engine path."""
    if not times:
        return "TIMEOUT" if timed_out else "n/a"
    return (
        f"min={min(times) * 1000:8.2f}ms  "
        f"avg={statistics.mean(times) * 1000:8.2f}ms  "
        f"max={max(times) * 1000:8.2f}ms"
    )


def print_report(
    pg: dict,
    mg: dict,
    max_hops: int,
    *,
    start_id: int,
    iterations: int,
    pg_timeout_ms: int,
) -> None:
    PG_W, MG_W, SP_W = 14, 14, 9
    bar = "═" * 70

    print()
    print(bar)
    print("  N-hop reachability  —  Pokec medium dataset")
    print("  Postgres 19 (SQL/PGQ GRAPH_TABLE)   vs   Memgraph (Cypher *BFS)")
    print(bar)
    print()
    print(
        f"  {'Hops':>4}  "
        f"{'Postgres':>{PG_W}}  "
        f"{'Memgraph':>{MG_W}}  "
        f"{'Speedup':>{SP_W}}"
    )
    print("  " + "─" * (4 + 2 + PG_W + 2 + MG_W + 2 + SP_W))

    for n in range(1, max_hops + 1):
        pg_info, mg_info = pg[n], mg[n]
        pg_t, mg_t = pg_info["times"], mg_info["times"]
        pg_str = fmt_time(pg_t, pg_info.get("timed_out"))
        mg_str = fmt_time(mg_t, mg_info.get("timed_out"))
        if pg_t and mg_t:
            speedup = f"{statistics.mean(pg_t) / statistics.mean(mg_t):.1f}×"
        else:
            speedup = "—"
        print(
            f"  {n:>4}  "
            f"{pg_str:>{PG_W}}  "
            f"{mg_str:>{MG_W}}  "
            f"{speedup:>{SP_W}}"
        )

    footer_parts = [
        f"iterations/hop: {iterations}",
        f"start user: {start_id}",
    ]
    if pg_timeout_ms > 0:
        footer_parts.append(f"pg timeout: {pg_timeout_ms // 1000}s")
    print()
    print("  " + "  ·  ".join(footer_parts))
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-id", type=int, default=40692)
    parser.add_argument("--max-hops", type=int, default=5)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--skip-postgres", action="store_true")
    parser.add_argument("--skip-memgraph", action="store_true")
    parser.add_argument(
        "--pg-timeout-ms",
        type=int,
        default=30_000,
        help="Postgres statement_timeout in ms (0 = no timeout). Default: 30000.",
    )
    args = parser.parse_args()

    if not (1 <= args.max_hops <= MAX_SUPPORTED_HOPS):
        parser.error(f"--max-hops must be between 1 and {MAX_SUPPORTED_HOPS}")

    pg_results: dict = {}
    mg_results: dict = {}

    if not args.skip_postgres:
        print(">>> benchmarking Postgres")
        pg_results = benchmark_postgres(
            args.start_id, args.max_hops, args.iterations, args.pg_timeout_ms
        )
    if not args.skip_memgraph:
        print(">>> benchmarking Memgraph")
        mg_results = benchmark_memgraph(args.start_id, args.max_hops, args.iterations)

    if pg_results and mg_results:
        print_report(
            pg_results,
            mg_results,
            args.max_hops,
            start_id=args.start_id,
            iterations=args.iterations,
            pg_timeout_ms=args.pg_timeout_ms,
        )
    else:
        for label, res in (("postgres", pg_results), ("memgraph", mg_results)):
            if not res:
                continue
            print(f"\n=== {label} ===")
            for n, info in res.items():
                print(f"  {n}-hop  {fmt(info['times'], info.get('timed_out'))}")


if __name__ == "__main__":
    main()
