"""
FastAPI service that exposes Memgraph query results as tabular JSON.

Power BI connects to this via Get Data > Web connector.

Endpoints:
    GET /nodes              — all nodes as flat rows
    GET /edges              — all edges as flat rows
    GET /person-purchases   — persons with their purchases (flattened)
    GET /company-employees  — companies with employee count and list
    POST /query             — run arbitrary Cypher, returns list of dicts
"""

import os

from fastapi import FastAPI, HTTPException
from neo4j import GraphDatabase
from pydantic import BaseModel

MG_HOST = os.getenv("MEMGRAPH_HOST", "localhost")
MG_PORT = int(os.getenv("MEMGRAPH_PORT", "7687"))

app = FastAPI(title="Memgraph Power BI API")

_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(f"bolt://{MG_HOST}:{MG_PORT}", auth=("", ""))
    return _driver


def run_query(cypher: str, params: dict | None = None) -> list[dict]:
    with get_driver().session() as session:
        result = session.run(cypher, params or {})
        return [record.data() for record in result]


# ---------------------------------------------------------------------------
# Pre-built endpoints (recommended for Power BI)
# ---------------------------------------------------------------------------


@app.get("/nodes")
def get_nodes():
    """Return all nodes as flat rows with id, label, and properties."""
    return run_query("""
        MATCH (n)
        RETURN n.id AS id,
               labels(n)[0] AS label,
               n.name AS name,
               n.age AS age,
               n.revenue AS revenue,
               n.price AS price
    """)


@app.get("/edges")
def get_edges():
    """Return all edges as flat rows."""
    return run_query("""
        MATCH (a)-[r]->(b)
        RETURN a.id AS source_id,
               a.name AS source_name,
               type(r) AS relationship,
               b.id AS target_id,
               b.name AS target_name,
               r.since AS since,
               r.quantity AS quantity
    """)


@app.get("/person-purchases")
def get_person_purchases():
    """Persons with their product purchases — good for Power BI tables/charts."""
    return run_query("""
        MATCH (p:Person)-[b:BOUGHT]->(prod:Product)
        RETURN p.name AS person,
               p.age AS age,
               prod.name AS product,
               prod.price AS unit_price,
               b.quantity AS quantity,
               prod.price * b.quantity AS total_spent
    """)


@app.get("/company-employees")
def get_company_employees():
    """Companies with employee details."""
    return run_query("""
        MATCH (p:Person)-[w:WORKS_AT]->(c:Company)
        RETURN c.name AS company,
               c.revenue AS company_revenue,
               p.name AS employee,
               p.age AS employee_age,
               w.since AS employed_since
    """)


# ---------------------------------------------------------------------------
# Flexible Cypher endpoint
# ---------------------------------------------------------------------------


class CypherRequest(BaseModel):
    query: str
    params: dict | None = None


@app.post("/query")
def run_custom_query(req: CypherRequest):
    """Run arbitrary Cypher and return results as a list of dicts."""
    try:
        return run_query(req.query, req.params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
