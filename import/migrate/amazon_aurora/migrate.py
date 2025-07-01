import mysql.connector
from gqlalchemy import Memgraph
import random
import string
import time

# Configuration
AURORA_HOST = "localhost"
AURORA_PORT = 3306
AURORA_USER = "testuser"
AURORA_PASSWORD = "testpass"
AURORA_DATABASE = "testdb"

MEMGRAPH_HOST = "localhost"
MEMGRAPH_PORT = 7688

# Configuration for the complete migration
TABLES = [f"Table{i}" for i in range(1, 6)]  # Table1, Table2, ..., Table5
ROWS_PER_TABLE = 100
RELATIONSHIP_TABLES = [f"RelTable{i}" for i in range(1, 5)]  # RelTable1, RelTable2, ..., RelTable4


def generate_string(length=50):
    """Generate a random string for table properties."""
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def get_aurora_connection():
    """Get a connection to Aurora MySQL."""
    return mysql.connector.connect(
        host=AURORA_HOST,
        port=AURORA_PORT,
        user=AURORA_USER,
        password=AURORA_PASSWORD,
        database=AURORA_DATABASE
    )


def ensure_aurora_has_data():
    """Ensure Aurora has the required data structure."""
    connection = get_aurora_connection()
    cursor = connection.cursor()
    
    print("Clearing existing data in Aurora...")
    
    # Drop all existing tables
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for table in tables:
        table_name = table[0]
        cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")
        print(f"Dropped table: {table_name}")
    
    print("Creating complete dataset in Aurora...")
    
    # Create tables with relationships
    for i, table_name in enumerate(TABLES):
        print(f"Creating table {table_name}...")
        
        # Create main table
        create_table_query = f"""
        CREATE TABLE `{table_name}` (
            id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            created_at DATE,
            active BOOLEAN,
            value1 INT,
            value2 DECIMAL(10,2),
            metadata JSON
        )
        """
        cursor.execute(create_table_query)
        
        # Create index on id column
        create_index_query = f"CREATE INDEX idx_{table_name}_id ON `{table_name}` (id)"
        cursor.execute(create_index_query)
        
        # Insert data into table
        print(f"Populating {table_name} with {ROWS_PER_TABLE} rows...")
        for j in range(ROWS_PER_TABLE):
            row_data = {
                "id": f"{table_name.lower()}_{j}",
                "name": f"{table_name} Row {j}",
                "description": generate_string(),
                "created_at": f"2024-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}",
                "active": random.choice([True, False]),
                "value1": random.randint(1, 1000),
                "value2": round(random.uniform(0.0, 1000.0), 2),
                "metadata": f'{{"category": "cat_{random.randint(1, 5)}", "priority": {random.randint(1, 10)}}}'
            }
            
            insert_query = f"""
            INSERT INTO `{table_name}` (id, name, description, created_at, active, value1, value2, metadata)
            VALUES (%(id)s, %(name)s, %(description)s, %(created_at)s, %(active)s, %(value1)s, %(value2)s, %(metadata)s)
            """
            cursor.execute(insert_query, row_data)
    
    # Create relationship tables
    for i in range(len(TABLES) - 1):
        table1 = TABLES[i]
        table2 = TABLES[i + 1]
        rel_table_name = RELATIONSHIP_TABLES[i]
        
        print(f"Creating relationship table {rel_table_name} between {table1} and {table2}...")
        
        create_rel_table_query = f"""
        CREATE TABLE `{rel_table_name}` (
            id INT AUTO_INCREMENT PRIMARY KEY,
            from_id VARCHAR(50),
            to_id VARCHAR(50),
            relationship_type VARCHAR(50),
            strength DECIMAL(3,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_id) REFERENCES `{table1}`(id) ON DELETE CASCADE,
            FOREIGN KEY (to_id) REFERENCES `{table2}`(id) ON DELETE CASCADE
        )
        """
        cursor.execute(create_rel_table_query)
        
        # Create relationships between all rows of consecutive tables
        cursor.execute(f"SELECT id FROM `{table1}`")
        from_ids = [row[0] for row in cursor.fetchall()]
        
        cursor.execute(f"SELECT id FROM `{table2}`")
        to_ids = [row[0] for row in cursor.fetchall()]
        
        # Create relationships between all combinations
        for from_id in from_ids:
            for to_id in to_ids:
                rel_data = {
                    "from_id": from_id,
                    "to_id": to_id,
                    "relationship_type": f"RELATES_TO_{i+1}",
                    "strength": round(random.uniform(0.1, 1.0), 2)
                }
                
                insert_rel_query = f"""
                INSERT INTO `{rel_table_name}` (from_id, to_id, relationship_type, strength)
                VALUES (%(from_id)s, %(to_id)s, %(relationship_type)s, %(strength)s)
                """
                cursor.execute(insert_rel_query, rel_data)
        
        print(f"Created {len(from_ids) * len(to_ids)} relationships in {rel_table_name}")
    
    connection.commit()
    cursor.close()
    connection.close()
    print("Aurora data creation complete.")


def migrate_with_gqlalchemy():
    """Migrate data from Aurora to Memgraph using explicit SQL queries."""
    try:
        print("[Worker 1] Connecting to Memgraph...")
        memgraph = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)

        print("[Worker 1] Setting storage mode and clearing graph...")
        memgraph.execute("STORAGE MODE IN_MEMORY_ANALYTICAL")
        memgraph.execute("DROP GRAPH")

        print("[Worker 1] Creating necessary indices...")
        memgraph.execute("CREATE INDEX ON :__MigrationNode__(__unique_id__)")

        print("[Worker 1] Verifying Aurora connectivity...")
        # Test connection to Aurora
        test_result = list(memgraph.execute_and_fetch(
            """
            CALL migrate.mysql("SELECT 1 as test", {
                host: "aurora",
                port: 3306,
                user: "testuser",
                password: "testpass",
                database: "testdb"
            }) YIELD row RETURN row.test as test_value
            """
        ))
        print(f"[Worker 1] Aurora connectivity test result: {test_result[0]['test_value']}")

        print("[Worker 1] Starting migration from Aurora to Memgraph...")
        
        # Migrate Table1-Table6 as nodes
        for table_name in TABLES:
            print(f"[Worker 1] Migrating {table_name} as nodes...")
            
            # Create nodes directly from Aurora data
            memgraph.execute(
                f"""
                CALL migrate.mysql("SELECT * FROM `{table_name}`", {{
                    host: "aurora",
                    port: 3306,
                    user: "testuser",
                    password: "testpass",
                    database: "testdb"
                }}) YIELD row
                CREATE (n:{table_name}:__MigrationNode__)
                SET n += row, n.__unique_id__ = "{table_name}_" + row.id
                """
            )
            
            print(f"[Worker 1] Created {table_name} nodes")

        # Migrate RelTable relationships
        for i, rel_table_name in enumerate(RELATIONSHIP_TABLES):
            print(f"[Worker 1] Migrating {rel_table_name} relationships...")
            
            # Create relationships directly from Aurora data
            memgraph.execute(
                f"""
                CALL migrate.mysql("SELECT * FROM `{rel_table_name}`", {{
                    host: "aurora",
                    port: 3306,
                    user: "testuser",
                    password: "testpass",
                    database: "testdb"
                }}) YIELD row
                MATCH (a:__MigrationNode__ {{__unique_id__: "Table{i+1}_" + row.from_id}}), (b:__MigrationNode__ {{__unique_id__: "Table{i+2}_" + row.to_id}})
                CREATE (a)-[r:{rel_table_name} {{
                    strength: row.strength,
                    created_at: row.created_at
                }}]->(b)
                """
            )
            
            print(f"[Worker 1] Created {rel_table_name} relationships")

        print("[Worker 1] Migration completed.")

        print("[Worker 1] Verifying migration results...")
        
        # Count nodes and relationships
        node_count = list(memgraph.execute_and_fetch("MATCH (n) RETURN count(n) as count"))
        print(f"[Worker 1] Total nodes in Memgraph: {node_count[0]['count']}")
        
        relationship_count = list(memgraph.execute_and_fetch("MATCH ()-[r]->() RETURN count(r) as count"))
        print(f"[Worker 1] Total relationships in Memgraph: {relationship_count[0]['count']}")

        print("[Worker 1] Creating snapshot...")
        memgraph.execute("CREATE SNAPSHOT")

    except Exception as e:
        print(f"[Worker 1] Error during migration: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main function to orchestrate the complete migration process."""
    print("=== Complete Migration from Amazon Aurora to Memgraph ===")
    
    # Step 1: Ensure Aurora has the required data
    print("\n1. Setting up Aurora data...")
    ensure_aurora_has_data()

    # Step 3: Wait a moment for services to be ready
    print("\n3. Waiting for services to be ready...")
    time.sleep(5)
    
    # Step 4: Perform migration
    print("\n4. Starting migration to Memgraph...")
    migrate_with_gqlalchemy()
    
    print("\n=== Migration Complete ===")


if __name__ == "__main__":
    main() 