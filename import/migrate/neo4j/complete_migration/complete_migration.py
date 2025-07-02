from neo4j import GraphDatabase
from gqlalchemy import Memgraph
import random
import string

NEO4J_URI = "bolt://localhost:7687"
MEMGRAPH_HOST = "localhost"
MEMGRAPH_PORT = 7688

# Configuration for the complete migration
LABELS = [f"Label{i}" for i in range(1, 11)]  # Label1, Label2, ..., Label10
NODES_PER_LABEL = 100
RELATIONSHIP_TYPES = ["RELATES_TO_1", "RELATES_TO_2", "RELATES_TO_3", "RELATES_TO_4", "RELATES_TO_5", 
                      "RELATES_TO_6", "RELATES_TO_7", "RELATES_TO_8", "RELATES_TO_9", "RELATES_TO_10"]


def generate_string(length=50):
    """Generate a random string for node properties."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def ensure_neo4j_has_data():
    """Ensure Neo4j has the required data structure."""
    driver = GraphDatabase.driver(NEO4J_URI, auth=None)
    
    print("Clearing existing data in Neo4j...")
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    
    print("Creating complete dataset in Neo4j...")
    
    # Insert all nodes for all labels
    with driver.session() as session:
        for label in LABELS:
            print(f"Creating {NODES_PER_LABEL} {label} nodes...")
            batch = []
            for i in range(NODES_PER_LABEL):
                node_data = {
                    "id": f"{label.lower()}_{i}",
                    "name": f"{label} {i}",
                    "description": generate_string(),
                    "created_at": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                    "active": random.choice([True, False])
                }
                batch.append(node_data)
            
            # Insert nodes in batches
            batch_size = 50
            for i in range(0, len(batch), batch_size):
                current_batch = batch[i:i + batch_size]
                session.execute_write(
                    lambda tx: tx.run(
                        f"UNWIND $nodes AS node CREATE (:{label} {{id: node.id, name: node.name, description: node.description, created_at: node.created_at, active: node.active}})",
                        nodes=current_batch,
                    )
                )
    
    # Create chained relationships
    print("Creating chained relationships...")
    with driver.session() as session:
        for i in range(len(LABELS) - 1):
            label1 = LABELS[i]
            label2 = LABELS[i + 1]
            rel_type = RELATIONSHIP_TYPES[i]
            
            # Create relationships between all nodes of consecutive labels
            query = f"""
            MATCH (a:{label1}), (b:{label2})
            CREATE (a)-[r:{rel_type} {{strength: {random.random()}, created_at: datetime()}}]->(b)
            """
            session.run(query)
            
            print(f"Created {rel_type} relationships between all {label1} nodes and all {label2} nodes")
    
    driver.close()
    print("Neo4j data creation complete.")


def inspect_neo4j_schema(driver):
    """Inspect the Neo4j schema to understand labels and relationship types."""
    with driver.session() as session:
        # Get schema using apoc.meta.schema()
        schema_result = session.run("CALL apoc.meta.schema() YIELD value RETURN value")
        schema_data = schema_result.single()["value"]
        
        # Extract labels and relationship types from schema
        discovered_labels = []
        discovered_rel_types = []
        
        for key, info in schema_data.items():
            if info.get("type") == "node":
                discovered_labels.append(key)
                print(f"[Worker 1] Discovered node label: {key} (count: {info.get('count', 'unknown')})")
            elif info.get("type") == "relationship":
                discovered_rel_types.append(key)
                print(f"[Worker 1] Discovered relationship type: {key} (count: {info.get('count', 'unknown')})")
        
        return {
            "labels": discovered_labels,
            "relationship_types": discovered_rel_types,
            "label_counts": {label: info.get('count', 'unknown') for label, info in schema_data.items() if info.get("type") == "node"},
            "relationship_counts": {rel_type: info.get('count', 'unknown') for rel_type, info in schema_data.items() if info.get("type") == "relationship"}
        }


def migrate_with_gqlalchemy():
    """Migrate data from Neo4j to Memgraph using the migrate.neo4j module with apoc.meta.schema()."""
    try:
        print("[Worker 1] Connecting to Memgraph...")
        memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
        
        def execute_query(query):
            print(query)
            memgraph.execute(query)

        print("[Worker 1] Setting storage mode and clearing graph...")
        execute_query("STORAGE MODE IN_MEMORY_ANALYTICAL")
        execute_query("DROP GRAPH")

        print("[Worker 1] Creating __MigrationNode__ index on __elementId__...")
        execute_query("CREATE INDEX ON :__MigrationNode__(__elementId__)")

        print("[Worker 1] Verifying Neo4j connectivity...")
        execute_query(
            """
            call migrate_neo4j_driver2.neo4j("RETURN 1;", {host: "neo4j", port: 7687}) YIELD row RETURN row;
            """
        )

        print("[Worker 1] Discovering Neo4j schema using apoc.meta.schema()...")
        
        # Get comprehensive schema information using apoc.meta.schema()
        schema_result = list(memgraph.execute_and_fetch(
            """
            call migrate_neo4j_driver2.neo4j("CALL apoc.meta.schema() YIELD value RETURN value", {host: "neo4j", port: 7687}) YIELD row RETURN row.value as schema
            """
        ))
        
        schema_data = schema_result[0]["schema"]
        
        # Extract labels and relationship types from schema
        discovered_labels = []
        discovered_rel_types = []
        
        for key, info in schema_data.items():
            if info.get("type") == "node":
                discovered_labels.append(key)
                print(f"[Worker 1] Discovered node label: {key} (count: {info.get('count', 'unknown')})")
            elif info.get("type") == "relationship":
                discovered_rel_types.append(key)
                print(f"[Worker 1] Discovered relationship type: {key} (count: {info.get('count', 'unknown')})")
        
        # Create indexes for all discovered labels
        for label in discovered_labels:
            memgraph.execute(f"CREATE INDEX ON :{label}")
            memgraph.execute(f"CREATE INDEX ON :{label}(id)")

        print("[Worker 1] Starting migration of nodes...")
        
        # Migrate nodes for each discovered label with __elementId__
        for label in discovered_labels:
            print(f"[Worker 1] Migrating {label} nodes...")
            execute_query(
                f"""
                call migrate_neo4j_driver2.neo4j(
                    "MATCH (n:{label}) RETURN elementId(n) AS elementId, labels(n) as labels, properties(n) AS props",
                    {{host: "neo4j", port: 7687}}
                ) YIELD row
                MERGE (n:{label}:__MigrationNode__ {{__elementId__: row.elementId}})
                SET n:row.labels
                SET n += row.props
                """
            )
            print(f"[Worker 1] Completed migration of {label} nodes")

        print("[Worker 1] Starting migration of relationships...")
        
        # Migrate relationships for each discovered type using __elementId__ for matching
        for rel_type in discovered_rel_types:
            print(f"[Worker 1] Migrating {rel_type} relationships...")
            execute_query(
                f"""
                call migrate_neo4j_driver2.neo4j(
                    "MATCH (a)-[r:{rel_type}]->(b) RETURN elementId(a) AS from_elementId, elementId(b) AS to_elementId, properties(r) AS rel_props",
                    {{host: "neo4j", port: 7687}}
                ) YIELD row
                MATCH (a:__MigrationNode__ {{__elementId__: row.from_elementId}})
                MATCH (b:__MigrationNode__ {{__elementId__: row.to_elementId}})
                CREATE (a)-[r:{rel_type}]->(b)
                SET r += row.rel_props
                """
            )
            print(f"[Worker 1] Completed migration of {rel_type} relationships")

        print("[Worker 1] Migration complete.")
        
        # Verify migration results
        print("[Worker 1] Verifying migration results...")
        for label in discovered_labels:
            result = list(memgraph.execute_and_fetch(f"MATCH (n:{label}) RETURN count(n) as count"))
            count = result[0]["count"]
            print(f"[Worker 1] {label} nodes in Memgraph: {count}")
        
        for rel_type in discovered_rel_types:
            result = list(memgraph.execute_and_fetch(f"MATCH ()-[r:{rel_type}]->() RETURN count(r) as count"))
            count = result[0]["count"]
            print(f"[Worker 1] {rel_type} relationships in Memgraph: {count}")

        print("[Worker 1] Creating snapshot...")
        memgraph.execute("CREATE SNAPSHOT")

    except Exception as e:
        print(f"[Worker 1] Error during migration: {e}")


def main():
    """Main function to orchestrate the complete migration process."""
    print("=== Complete Migration from Neo4j to Memgraph ===")
    
    # Step 1: Ensure Neo4j has the required data
    print("\n1. Setting up Neo4j data...")
    ensure_neo4j_has_data()
    
    # Step 2: Inspect Neo4j schema
    print("\n2. Inspecting Neo4j schema...")
    driver = GraphDatabase.driver(NEO4J_URI, auth=None)
    schema_info = inspect_neo4j_schema(driver)
    driver.close()
    
    print("Neo4j Schema Information:")
    print(f"Labels: {schema_info['labels']}")
    print(f"Relationship Types: {schema_info['relationship_types']}")
    print("Node counts per label:")
    for label, count in schema_info['label_counts'].items():
        print(f"  {label}: {count}")
    print("Relationship counts per type:")
    for rel_type, count in schema_info['relationship_counts'].items():
        print(f"  {rel_type}: {count}")
    
    # Step 3: Perform migration
    print("\n3. Starting migration to Memgraph...")
    migrate_with_gqlalchemy()
    
    print("\n=== Migration Complete ===")


if __name__ == "__main__":
    main() 