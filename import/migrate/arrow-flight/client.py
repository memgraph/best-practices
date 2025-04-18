from neo4j import GraphDatabase

HOST_PORT = "bolt://localhost:7687"

if __name__ == "__main__":
    driver = GraphDatabase.driver(HOST_PORT, auth=("", ""))

    records, summary, keys = driver.execute_query(
        "CALL migrate.arrow_flight('SELECT * FROM numbers', {host: 'host.docker.internal',port: '50051'} ) YIELD row CREATE (n:Number {name: row.numbers}) RETURN n;"
    )

    print("Created %d nodes" % summary.counters.nodes_created)

    driver.close()
