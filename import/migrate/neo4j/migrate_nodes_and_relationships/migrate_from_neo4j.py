from neo4j import GraphDatabase
from gqlalchemy import Memgraph
from multiprocessing import Event, Process
import random
import string
import time

NEO4J_URI = "bolt://localhost:7687"
MEMGRAPH_HOST = "localhost"
MEMGRAPH_PORT = 7688

TARGET_PAIR_COUNT = 10_000_000
BATCH_SIZE = 1_000_000


def get_random_label() -> str:
    rand = random.randint(1, 10)
    return f"Label{rand}"


def generate_string(length=100):
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def get_existing_node_count(driver):
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) AS count;")
        return result.single()["count"]


def insert_nodes(driver, start_index, batch_size):
    with driver.session() as session:
        batch = [
            {"message": generate_string(), "id": start_index + j}
            for j in range(batch_size)
        ]
        label = get_random_label()
        session.execute_write(
            lambda tx: tx.run(
                f"UNWIND $nodes AS node CREATE (:Label{label} {{id: node.id, message: node.message}})-[:NEXT]->(:Label{label} {{id: node.id, message: node.message}});",
                nodes=batch,
            )
        )


def ensure_neo4j_has_data():
    driver = GraphDatabase.driver(NEO4J_URI, auth=None)
    current_count = get_existing_node_count(driver)
    print(f"Neo4j currently has {current_count} nodes.")

    if current_count >= TARGET_PAIR_COUNT:
        print("No additional data needs to be inserted.")
        driver.close()
        return

    remaining = TARGET_PAIR_COUNT - current_count
    batches = remaining // BATCH_SIZE

    print(f"Inserting {remaining} more pairs in {batches} batches...")
    for i in range(batches):
        insert_nodes(driver, current_count + i * BATCH_SIZE, BATCH_SIZE)
        print(f"Inserted batch {i+1}/{batches}")
    driver.close()
    print("Neo4j data creation complete.")


def migrate_with_gqlalchemy(done_event):
    try:
        print("[Worker 1] Connecting to Memgraph...")
        memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)

        print("[Worker 1] Setting storage mode and clearing graph...")
        memgraph.execute("STORAGE MODE IN_MEMORY_ANALYTICAL")
        memgraph.execute("DROP GRAPH")
        for i in range(1, 11):
            memgraph.execute(f"CREATE INDEX ON :Label{i}")
            memgraph.execute(f"CREATE INDEX ON :Label{i}(id)")

        print("[Worker 1] Verifying Neo4j connectivity...")
        memgraph.execute(
            """
            CALL migrate.neo4j("RETURN 1;", {host: "neo4j", port: 7687}) YIELD row RETURN row;
        """
        )

        print("[Worker 1] Starting migration...")
        print("[Worker 1] Starting node migration...")
        memgraph.execute(
            """
            CALL migrate.neo4j(
                "MATCH (p) RETURN labels(p)[0] as node_label, p.id AS id, properties(p) AS props",
                {host: "neo4j", port: 7687}
            ) YIELD row
            CREATE (p:row.node_label {id: row.id})
            SET p.message = row.props.message;
        """
        )
        print("[Worker 1] Node migration complete...")
        print("[Worker 1] Starting relationship migration...")
        for i in range(1, 11):
            memgraph.execute(
                f"""
                CALL migrate.neo4j(
                    "MATCH (n:Label{i})-[r]->(m:Label{i}) RETURN n.id as nid, m.id as mid",
                    {{host: "neo4j", port: 7687}}
                ) YIELD row
                MATCH (n:Label{i} {{id: row.nid}})
                MATCH (m:Label{i} {{id: row.mid}})
                CREATE (n)-[:NEXT]->(m);
            """
            )
        print("[Worker 1] Relationship migration complete...")
        print("[Worker 1] Migration complete.")
    finally:
        done_event.set()


def monitor_storage_info(done_event):
    print("[Worker 2] Monitoring Memgraph storage info...")
    memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
    start = time.time()
    while not done_event.is_set():
        try:
            result = memgraph.execute_and_fetch("SHOW STORAGE INFO")
            vertex_count = None
            memory_tracked = None
            for row in result:
                if row.get("storage info") == "vertex_count":
                    vertex_count = row.get("value")
                elif row.get("storage info") == "memory_tracked":
                    memory_tracked = row.get("value")
            print(
                f"[Worker 2] Vertices: {vertex_count}, Memory Used: {memory_tracked} bytes"
            )
            time.sleep(5)
            elapsed_time = time.time() - start
            print(f"Elapsed time: {elapsed_time}s")
        except Exception as e:
            print(f"[Worker 2] Error: {e}")
            break
    print("[Worker 2] Monitoring stopped.")


if __name__ == "__main__":
    ensure_neo4j_has_data()

    done_event = Event()
    p1 = Process(target=migrate_with_gqlalchemy, args=(done_event,))
    p2 = Process(target=monitor_storage_info, args=(done_event,))

    p1.start()
    p2.start()

    p1.join()
    print("[Main] Migration process finished.")

    p2.join()
    print("[Main] Monitor process finished.")
