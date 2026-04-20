"""Verify that Liquibase migrations were applied to Memgraph.

Connects to Memgraph and checks that the expected graph structure exists,
including nodes, relationships, and Liquibase's internal history graph.
"""

from neo4j import GraphDatabase

URI = "bolt://localhost:7687"


def main():
    driver = GraphDatabase.driver(URI)

    with driver.session() as session:
        # 1. Check Person nodes
        result = session.run("MATCH (p:Person) RETURN p.name AS name, p.email AS email, p.role AS role, p.active AS active ORDER BY p.name")
        persons = list(result)
        print(f"Person nodes: {len(persons)}")
        for record in persons:
            print(f"  - {record['name']} ({record['email']}) role={record['role']} active={record['active']}")

        # 2. Check Company nodes
        result = session.run("MATCH (c:Company) RETURN c.name AS name, c.founded AS founded, c.domain AS domain ORDER BY c.name")
        companies = list(result)
        print(f"\nCompany nodes: {len(companies)}")
        for record in companies:
            print(f"  - {record['name']} (founded {record['founded']}, domain: {record['domain']})")

        # 3. Check WORKS_AT relationships
        result = session.run(
            "MATCH (p:Person)-[r:WORKS_AT]->(c:Company) "
            "RETURN p.name AS person, c.name AS company, r.since AS since, r.department AS department "
            "ORDER BY p.name"
        )
        works_at = list(result)
        print(f"\nWORKS_AT relationships: {len(works_at)}")
        for record in works_at:
            print(f"  - {record['person']} -> {record['company']} (since {record['since']}, dept: {record['department']})")

        # 4. Check KNOWS relationships
        result = session.run(
            "MATCH (a:Person)-[r:KNOWS]->(b:Person) "
            "RETURN a.name AS from_person, b.name AS to_person, r.context AS context "
            "ORDER BY a.name"
        )
        knows = list(result)
        print(f"\nKNOWS relationships: {len(knows)}")
        for record in knows:
            print(f"  - {record['from_person']} -> {record['to_person']} ({record['context']})")

        # 5. Check Liquibase history (internal tracking nodes)
        result = session.run("MATCH (n) WHERE any(label IN labels(n) WHERE label STARTS WITH '__Liquibase') RETURN labels(n) AS labels, count(*) AS count")
        history = list(result)
        if history:
            print("\nLiquibase history graph:")
            for record in history:
                print(f"  - {record['labels']}: {record['count']} node(s)")
        else:
            print("\nLiquibase history graph: not found (extension may store history differently)")

        # 6. Summary
        result = session.run("MATCH (n) RETURN count(n) AS nodes")
        node_count = result.single()["nodes"]
        result = session.run("MATCH ()-[r]->() RETURN count(r) AS rels")
        rel_count = result.single()["rels"]
        print(f"\nGraph summary: {node_count} nodes, {rel_count} relationships")

    driver.close()
    print("\nVerification complete.")


if __name__ == "__main__":
    main()
