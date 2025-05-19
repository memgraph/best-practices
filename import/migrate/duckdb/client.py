from neo4j import GraphDatabase

HOST_PORT = "bolt://localhost:7687"

if __name__ == "__main__":
    driver = GraphDatabase.driver(HOST_PORT, auth=("", ""))

    records, summary, keys = driver.execute_query(
        """
        CALL migrate.duckdb("SELECT * FROM '/usr/lib/memgraph/data/users.csv';")
        YIELD row
        CREATE (n:User {id: row.id, age: row.age, name: row.name})
        RETURN n;
        """
    )

    print("Created %d nodes" % summary.counters.nodes_created)

    driver.close()
