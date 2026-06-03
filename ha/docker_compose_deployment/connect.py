#!/usr/bin/env python3
"""Connect to the Memgraph HA cluster through a single coordinator and run a
small end-to-end sanity check using the official Neo4j Python driver.

Topology (see docker-compose.yml / HA_register.cypherl):
  * 3 coordinators  - coord1/2/3 on bolt ports 7691/7692/7693
  * 3 data instances - instance1/2/3 on bolt ports 7687/7688/7689
                       (instance_1 starts as MAIN, the others are REPLICAs)

How clients talk to an HA cluster:
  * Use the routing-aware ``neo4j://`` scheme pointed at a coordinator. The
    coordinator returns a routing table, so write transactions go to the
    current MAIN and reads can be served by REPLICAs. This survives failovers.
  * Coordinator management queries (e.g. ``SHOW INSTANCES``) are NOT routable -
    for those you open a plain ``bolt://`` connection straight to a coordinator.

What this script tests:
  1. SHOW INSTANCES on a coordinator and assert the whole cluster is present.
  2. Write a node through the coordinator (routed to MAIN).
  3. Open a direct bolt connection to a REPLICA and assert the node replicated.
  4. Delete the node through the coordinator.
  5. Assert the REPLICA is empty again.

Usage:
    python connect.py            # connect through coord1 (default)
    python connect.py coord2     # connect through coord2

Requires:
    pip install neo4j
"""

import sys
import time

from neo4j import GraphDatabase

# Each coordinator exposes a bolt endpoint on the host.
COORDINATOR_PORTS = {
    "coord1": 7691,
    "coord2": 7692,
    "coord3": 7693,
}

# Direct bolt endpoint of a data instance that is a REPLICA at startup
# (instance_1 is MAIN, so instance_2 / instance_3 are REPLICAs).
REPLICA_NAME = "instance2"
REPLICA_URI = "bolt://localhost:7688"

# The full set of instances SHOW INSTANCES must report: 3 coordinators + 3 data.
EXPECTED_INSTANCES = 6

# Memgraph runs without authentication by default.
AUTH = ("", "")

TEST_LABEL = "HACheck"
TEST_NAME = "connect.py"


def fail(message):
    print(f"  ✗ {message}")
    sys.exit(1)


def ok(message):
    print(f"  ✓ {message}")


def retry(fn, attempts=10, delay=0.5):
    """Replication is asynchronous; poll a REPLICA until the expectation holds."""
    last = None
    for _ in range(attempts):
        last = fn()
        if last:
            return True
        time.sleep(delay)
    return bool(last)


def test_show_instances(coordinator_uri):
    print("1) SHOW INSTANCES on the coordinator")
    # Plain bolt:// (no routing) so the query runs ON the coordinator itself.
    with GraphDatabase.driver(coordinator_uri, auth=AUTH) as driver:
        with driver.session() as session:
            rows = list(session.run("SHOW INSTANCES;"))

    names = [r["name"] for r in rows]
    for r in rows:
        print(f"     - {r['name']:<14} role={r['role']:<11} health={r['health']}")
    if len(rows) != EXPECTED_INSTANCES:
        fail(f"expected {EXPECTED_INSTANCES} instances, got {len(rows)}: {names}")
    ok(f"all {EXPECTED_INSTANCES} instances present")


def test_write_through_coordinator(coordinator_uri):
    print("2) Write a node through the coordinator (routed to MAIN)")
    # neo4j:// → routing: the write is forwarded to the current MAIN.
    with GraphDatabase.driver(coordinator_uri.replace("bolt://", "neo4j://"),
                              auth=AUTH) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(
                    f"CREATE (n:{TEST_LABEL} {{name: $name}})", name=TEST_NAME
                ).consume()
            )
    ok("write committed on MAIN")


def test_replica_has_node():
    print(f"3) Direct bolt to REPLICA ({REPLICA_NAME}) - assert node replicated")

    def check():
        with GraphDatabase.driver(REPLICA_URI, auth=AUTH) as driver:
            with driver.session() as session:
                count = session.run(
                    f"MATCH (n:{TEST_LABEL}) RETURN count(n) AS c"
                ).single()["c"]
        return count == 1

    if not retry(check):
        fail("node did not replicate to the REPLICA")
    ok("node is present on the REPLICA")


def test_delete_through_coordinator(coordinator_uri):
    print("4) Delete the node through the coordinator")
    with GraphDatabase.driver(coordinator_uri.replace("bolt://", "neo4j://"),
                              auth=AUTH) as driver:
        with driver.session() as session:
            session.execute_write(
                lambda tx: tx.run(f"MATCH (n:{TEST_LABEL}) DELETE n").consume()
            )
    ok("delete committed on MAIN")


def test_replica_is_empty():
    print(f"5) Direct bolt to REPLICA ({REPLICA_NAME}) - assert it is empty")

    def check():
        with GraphDatabase.driver(REPLICA_URI, auth=AUTH) as driver:
            with driver.session() as session:
                count = session.run(
                    f"MATCH (n:{TEST_LABEL}) RETURN count(n) AS c"
                ).single()["c"]
        return count == 0

    if not retry(check):
        fail("node was not deleted on the REPLICA")
    ok("REPLICA is empty again")


def main():
    coordinator = sys.argv[1] if len(sys.argv) > 1 else "coord1"
    port = COORDINATOR_PORTS.get(coordinator)
    if port is None:
        print(f"Unknown coordinator '{coordinator}'. "
              f"Use one of: {', '.join(COORDINATOR_PORTS)}.", file=sys.stderr)
        return 1

    coordinator_uri = f"bolt://localhost:{port}"
    print(f"Connecting to the HA cluster through {coordinator} "
          f"(bolt://localhost:{port})\n")

    test_show_instances(coordinator_uri)
    test_write_through_coordinator(coordinator_uri)
    test_replica_has_node()
    test_delete_through_coordinator(coordinator_uri)
    test_replica_is_empty()

    print("\nAll checks passed - the HA cluster is healthy. ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
