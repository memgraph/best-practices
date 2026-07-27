"""
Power BI Python Data Source script.

Usage:
  1. In Power BI Desktop, go to Get Data > Python script
  2. Paste this script (or reference this file)
  3. Power BI will pick up all pandas DataFrames defined in the script

Prerequisites:
  - Python environment with neo4j and pandas installed
  - Memgraph running on localhost:7687
"""

import pandas as pd
from neo4j import GraphDatabase

MEMGRAPH_URI = "bolt://localhost:7687"

driver = GraphDatabase.driver(MEMGRAPH_URI, auth=("", ""))


def query_to_df(cypher: str) -> pd.DataFrame:
    with driver.session() as session:
        result = session.run(cypher)
        return pd.DataFrame([record.data() for record in result])


# Power BI will detect each DataFrame variable and offer it as a table.

# All nodes
nodes = query_to_df("""
    MATCH (n)
    RETURN n.id AS id,
           labels(n)[0] AS label,
           n.name AS name,
           n.age AS age,
           n.revenue AS revenue,
           n.price AS price
""")

# All edges
edges = query_to_df("""
    MATCH (a)-[r]->(b)
    RETURN a.id AS source_id,
           a.name AS source_name,
           type(r) AS relationship,
           b.id AS target_id,
           b.name AS target_name,
           r.since AS since,
           r.quantity AS quantity
""")

# Person purchases (flattened for charts)
person_purchases = query_to_df("""
    MATCH (p:Person)-[b:BOUGHT]->(prod:Product)
    RETURN p.name AS person,
           p.age AS age,
           prod.name AS product,
           prod.price AS unit_price,
           b.quantity AS quantity,
           prod.price * b.quantity AS total_spent
""")

# Company employees
company_employees = query_to_df("""
    MATCH (p:Person)-[w:WORKS_AT]->(c:Company)
    RETURN c.name AS company,
           c.revenue AS company_revenue,
           p.name AS employee,
           p.age AS employee_age,
           w.since AS employed_since
""")

driver.close()
