from neo4j import GraphDatabase

def execute_query(tx, query):
    tx.run(query)

uris = ["neo4j://localhost:7691", "neo4j://localhost:7692", "neo4j://localhost:7693"]
for uri in uris:
    driver = GraphDatabase.driver(uri, auth=("", ""))
    with driver.session() as session:
        session.execute_write(execute_query, "CREATE (n)")
    driver.close()

for uri in uris:
    driver = GraphDatabase.driver(uri, auth=("", ""))
    with driver.session() as session:
        session.execute_read(execute_query, "MATCH (n) RETURN n")
    driver.close()
