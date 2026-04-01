"""Seed Memgraph with sample data for the Power BI demo."""

import os

from neo4j import GraphDatabase

MG_HOST = os.getenv("MEMGRAPH_HOST", "localhost")
MG_PORT = int(os.getenv("MEMGRAPH_PORT", "7687"))


def seed():
    driver = GraphDatabase.driver(f"bolt://{MG_HOST}:{MG_PORT}", auth=("", ""))

    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")

        session.run("CREATE INDEX ON :Person(id)")
        session.run("CREATE INDEX ON :Company(id)")
        session.run("CREATE INDEX ON :Product(id)")

        session.run("""
            UNWIND $rows AS r
            CREATE (p:Person {id: r.id, name: r.name, age: r.age})
        """, rows=[
            {"id": 1, "name": "Alice", "age": 34},
            {"id": 2, "name": "Bob", "age": 28},
            {"id": 3, "name": "Carol", "age": 45},
            {"id": 4, "name": "Dave", "age": 31},
            {"id": 5, "name": "Eve", "age": 52},
        ])

        session.run("""
            UNWIND $rows AS r
            CREATE (c:Company {id: r.id, name: r.name, revenue: r.revenue})
        """, rows=[
            {"id": 100, "name": "Acme Corp", "revenue": 500000},
            {"id": 101, "name": "Globex Inc", "revenue": 1200000},
            {"id": 102, "name": "Initech", "revenue": 300000},
        ])

        session.run("""
            UNWIND $rows AS r
            CREATE (p:Product {id: r.id, name: r.name, price: r.price})
        """, rows=[
            {"id": 200, "name": "Widget", "price": 49.99},
            {"id": 201, "name": "Gadget", "price": 149.99},
            {"id": 202, "name": "Gizmo", "price": 29.99},
        ])

        # Relationships
        session.run("""
            UNWIND $rows AS r
            MATCH (a:Person {id: r.src}), (b:Company {id: r.dst})
            CREATE (a)-[:WORKS_AT {since: r.since}]->(b)
        """, rows=[
            {"src": 1, "dst": 100, "since": 2018},
            {"src": 2, "dst": 100, "since": 2020},
            {"src": 3, "dst": 101, "since": 2015},
            {"src": 4, "dst": 101, "since": 2021},
            {"src": 5, "dst": 102, "since": 2019},
        ])

        session.run("""
            UNWIND $rows AS r
            MATCH (a:Person {id: r.src}), (b:Product {id: r.dst})
            CREATE (a)-[:BOUGHT {quantity: r.qty}]->(b)
        """, rows=[
            {"src": 1, "dst": 200, "qty": 3},
            {"src": 2, "dst": 201, "qty": 1},
            {"src": 3, "dst": 200, "qty": 5},
            {"src": 3, "dst": 202, "qty": 2},
            {"src": 4, "dst": 201, "qty": 1},
            {"src": 5, "dst": 202, "qty": 4},
        ])

        session.run("""
            UNWIND $rows AS r
            MATCH (a:Person {id: r.src}), (b:Person {id: r.dst})
            CREATE (a)-[:KNOWS]->(b)
        """, rows=[
            {"src": 1, "dst": 2},
            {"src": 1, "dst": 3},
            {"src": 2, "dst": 4},
            {"src": 3, "dst": 5},
            {"src": 4, "dst": 5},
        ])

    node_count = driver.session().run("MATCH (n) RETURN count(n) AS cnt").single()["cnt"]
    edge_count = driver.session().run("MATCH ()-[r]->() RETURN count(r) AS cnt").single()["cnt"]
    print(f"Seeded {node_count} nodes and {edge_count} edges.")

    driver.close()


if __name__ == "__main__":
    seed()
