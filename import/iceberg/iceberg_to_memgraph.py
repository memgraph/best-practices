"""Load users + transactions into Memgraph from a configurable source.

The source backend (PyIceberg, DuckDB) is swappable via --source. Only the
read side differs — the writer below is identical for every backend.

Use --workers N to fan out N parallel Bolt writer processes. The single
reader feeds a multiprocessing queue; each worker process drains it via
its own driver/session. Memgraph runs in analytical mode (set in
prepare_graph), so concurrent writes don't conflict.

The reported elapsed time covers the source -> Memgraph ingestion only:
schema setup and graph reset are excluded so the number reflects actual
data movement, not one-time bookkeeping.
"""
import argparse
import multiprocessing as mp
import time
from typing import Iterable

from neo4j import Driver, GraphDatabase, Session

from loaders import available_sources, get_loader
from loaders.base import Loader

USER_CREATE_QUERY = """
UNWIND $rows AS r
CREATE (u:User {id: r.user_id, name: r.name, email: r.email, country: r.country})
"""

USER_MERGE_QUERY = """
UNWIND $rows AS r
MERGE (u:User {id: r.user_id})
SET u.name    = r.name,
    u.email   = r.email,
    u.country = r.country
"""

USER_QUERIES = {"create": USER_CREATE_QUERY, "merge": USER_MERGE_QUERY}

TX_BATCH_QUERY = """
UNWIND $rows AS r
MATCH (a:User {id: r.from_user})
MATCH (b:User {id: r.to_user})
CREATE (a)-[:SENT {tx_id: r.tx_id, amount: r.amount, ts: r.timestamp}]->(b)
"""

_SHUTDOWN = "__SHUTDOWN__"  # string sentinel survives pickling across processes


def prepare_graph(session: Session) -> None:
    """Pre-ingestion setup: switch to analytical mode for fast bulk writes,
    wipe the graph (DROP GRAPH also clears schema/indexes), then create
    the label and label-property indexes used by the loader."""
    session.run("STORAGE MODE IN_MEMORY_ANALYTICAL")
    session.run("DROP GRAPH")
    session.run("CREATE INDEX ON :User")
    session.run("CREATE INDEX ON :User(id)")


def write_serial(
    session: Session, label: str, query: str, batches: Iterable[list[dict]]
) -> None:
    for i, batch in enumerate(batches, start=1):
        session.run(query, rows=batch)
        print(f"[{label}] batch {i} ({len(batch)} rows) done")


def _writer_process(uri: str, label: str, query: str, q: "mp.Queue") -> None:
    """Worker entry point. Each process owns its driver — the neo4j driver
    isn't safe to share across forked processes."""
    name = mp.current_process().name
    with GraphDatabase.driver(uri, auth=("", "")) as driver:
        with driver.session() as session:
            while True:
                item = q.get()
                if item == _SHUTDOWN:
                    return
                session.run(query, rows=item)
                print(f"[{label}] {name} finished batch ({len(item)} rows)")


def write_parallel(
    uri: str,
    label: str,
    query: str,
    batches: Iterable[list[dict]],
    n_workers: int,
) -> None:
    """Producer-consumer: the main process reads from the loader and pushes
    batches onto a multiprocessing queue; n_workers writer processes pull
    and run UNWIND/MERGE on their own Bolt sessions."""
    q: "mp.Queue" = mp.Queue(maxsize=n_workers * 4)
    procs = [
        mp.Process(
            target=_writer_process,
            args=(uri, label, query, q),
            name=f"writer-{label}-{i}",
        )
        for i in range(n_workers)
    ]
    for p in procs:
        p.start()
    try:
        for batch in batches:
            q.put(batch)
    finally:
        for _ in range(n_workers):
            q.put(_SHUTDOWN)
    for p in procs:
        p.join()


def ingest(
    driver: Driver,
    uri: str,
    loader: Loader,
    n_workers: int,
    user_query: str,
) -> float:
    """Time the source -> Memgraph ingestion (excludes prepare_graph)."""
    start = time.perf_counter()

    if n_workers <= 1:
        with driver.session() as session:
            write_serial(session, "users", user_query, loader.users())
            write_serial(session, "tx", TX_BATCH_QUERY, loader.transactions())
    else:
        # Users must finish before transactions: the tx batch MATCHes them.
        write_parallel(uri, "users", user_query, loader.users(), n_workers)
        write_parallel(uri, "tx", TX_BATCH_QUERY, loader.transactions(), n_workers)

    return time.perf_counter() - start


def dry_run(loader: Loader) -> float:
    """Iterate the loader without writing — times batch preparation only."""
    start = time.perf_counter()

    for label, batches in (("users", loader.users()), ("tx", loader.transactions())):
        for i, batch in enumerate(batches, start=1):
            print(f"[{label}] batch {i} ({len(batch)} rows) prepared")

    return time.perf_counter() - start


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load users + transactions into Memgraph from various sources."
    )
    parser.add_argument(
        "--source",
        choices=available_sources(),
        default="pyiceberg",
        help="Data source backend (default: pyiceberg).",
    )
    parser.add_argument(
        "--uri",
        default="bolt://localhost:7687",
        help="Memgraph Bolt URI (default: bolt://localhost:7687).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of parallel Bolt writer processes (default: 1).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="Rows per UNWIND batch / Bolt round trip (default: 10000).",
    )
    parser.add_argument(
        "--user-write",
        choices=tuple(USER_QUERIES),
        default="create",
        help="How to write user nodes: 'create' (faster, assumes clean graph) "
             "or 'merge' (idempotent, safe for re-runs). Default: create.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Iterate source batches without writing to Memgraph; reports prep time only.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    loader = get_loader(args.source, batch_size=args.batch_size)

    if args.dry_run:
        elapsed = dry_run(loader)
        print(
            f"[{args.source}, batch={args.batch_size}, dry-run] "
            f"Prepared source batches in {elapsed:.2f}s"
        )
        return

    with GraphDatabase.driver(args.uri, auth=("", "")) as driver:
        with driver.session() as session:
            prepare_graph(session)
        elapsed = ingest(
            driver, args.uri, loader, args.workers, USER_QUERIES[args.user_write]
        )

    print(
        f"[{args.source}, workers={args.workers}, batch={args.batch_size}, "
        f"user-write={args.user_write}] "
        f"Ingested into Memgraph in {elapsed:.2f}s"
    )


if __name__ == "__main__":
    main()
