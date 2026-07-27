"""
Push Memgraph data to a Power BI Push Dataset via the Power BI REST API.

This is the recommended approach for Power BI Service on Linux — no Gateway needed.

Setup:
  1. Register an app in Azure AD (Microsoft Entra ID):
     - Go to https://portal.azure.com > App registrations > New registration
     - Add API permission: Power BI Service > Dataset.ReadWrite.All
     - Create a client secret
  2. In Power BI Service, create a Push Dataset (or let this script create one)
  3. Set environment variables (see below)

Usage:
    python push_to_powerbi.py

Environment variables:
    MEMGRAPH_HOST       (default: localhost)
    MEMGRAPH_PORT       (default: 7687)
    AZURE_TENANT_ID     — Azure AD tenant ID
    AZURE_CLIENT_ID     — App registration client ID
    AZURE_CLIENT_SECRET — App registration client secret
    POWERBI_WORKSPACE_ID — Power BI workspace (group) ID
"""

import os
import sys

import requests
from neo4j import GraphDatabase

MG_HOST = os.getenv("MEMGRAPH_HOST", "localhost")
MG_PORT = int(os.getenv("MEMGRAPH_PORT", "7687"))
TENANT_ID = os.getenv("AZURE_TENANT_ID", "")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")
WORKSPACE_ID = os.getenv("POWERBI_WORKSPACE_ID", "")

DATASET_NAME = "Memgraph Data"
POWERBI_API = "https://api.powerbi.com/v1.0/myorg"


def get_access_token() -> str:
    """Get an OAuth2 token from Azure AD."""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    resp = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    })
    resp.raise_for_status()
    return resp.json()["access_token"]


def get_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def query_memgraph(cypher: str, params: dict | None = None) -> list[dict]:
    driver = GraphDatabase.driver(f"bolt://{MG_HOST}:{MG_PORT}", auth=("", ""))
    with driver.session() as session:
        result = session.run(cypher, params or {})
        rows = [record.data() for record in result]
    driver.close()
    return rows


def find_or_create_dataset(token: str) -> tuple[str, dict[str, str]]:
    """Find existing dataset or create a new Push Dataset. Returns (dataset_id, table_name_map)."""
    headers = get_headers(token)
    base = f"{POWERBI_API}/groups/{WORKSPACE_ID}" if WORKSPACE_ID else f"{POWERBI_API}"

    # Check if dataset already exists
    resp = requests.get(f"{base}/datasets", headers=headers)
    resp.raise_for_status()
    for ds in resp.json().get("value", []):
        if ds["name"] == DATASET_NAME:
            print(f"Found existing dataset: {ds['id']}")
            return ds["id"], {}

    # Create Push Dataset with two tables
    dataset_def = {
        "name": DATASET_NAME,
        "defaultMode": "Push",
        "tables": [
            {
                "name": "PersonPurchases",
                "columns": [
                    {"name": "person", "dataType": "String"},
                    {"name": "age", "dataType": "Int64"},
                    {"name": "product", "dataType": "String"},
                    {"name": "unit_price", "dataType": "Double"},
                    {"name": "quantity", "dataType": "Int64"},
                    {"name": "total_spent", "dataType": "Double"},
                ],
            },
            {
                "name": "CompanyEmployees",
                "columns": [
                    {"name": "company", "dataType": "String"},
                    {"name": "company_revenue", "dataType": "Int64"},
                    {"name": "employee", "dataType": "String"},
                    {"name": "employee_age", "dataType": "Int64"},
                    {"name": "employed_since", "dataType": "Int64"},
                ],
            },
        ],
    }

    resp = requests.post(f"{base}/datasets", headers=headers, json=dataset_def)
    resp.raise_for_status()
    dataset_id = resp.json()["id"]
    print(f"Created dataset: {dataset_id}")
    return dataset_id, {}


def push_rows(token: str, dataset_id: str, table_name: str, rows: list[dict]) -> None:
    """Push rows to a Power BI Push Dataset table."""
    headers = get_headers(token)
    base = f"{POWERBI_API}/groups/{WORKSPACE_ID}" if WORKSPACE_ID else f"{POWERBI_API}"
    url = f"{base}/datasets/{dataset_id}/tables/{table_name}/rows"

    # Power BI Push API accepts max 10,000 rows per request
    batch_size = 10_000
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        resp = requests.post(url, headers=headers, json={"rows": batch})
        resp.raise_for_status()

    print(f"  Pushed {len(rows)} rows to {table_name}")


def main() -> None:
    for var in ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]:
        if not os.getenv(var):
            print(f"Error: {var} environment variable is required.")
            print("See the docstring at the top of this file for setup instructions.")
            sys.exit(1)

    print("Authenticating with Azure AD ...")
    token = get_access_token()

    print("Setting up Power BI dataset ...")
    dataset_id, _ = find_or_create_dataset(token)

    print("Querying Memgraph ...")
    purchases = query_memgraph("""
        MATCH (p:Person)-[b:BOUGHT]->(prod:Product)
        RETURN p.name AS person,
               p.age AS age,
               prod.name AS product,
               prod.price AS unit_price,
               b.quantity AS quantity,
               prod.price * b.quantity AS total_spent
    """)

    employees = query_memgraph("""
        MATCH (p:Person)-[w:WORKS_AT]->(c:Company)
        RETURN c.name AS company,
               c.revenue AS company_revenue,
               p.name AS employee,
               p.age AS employee_age,
               w.since AS employed_since
    """)

    print("Pushing data to Power BI ...")
    push_rows(token, dataset_id, "PersonPurchases", purchases)
    push_rows(token, dataset_id, "CompanyEmployees", employees)

    print("\nDone. Open Power BI Service to build reports on the dataset.")


if __name__ == "__main__":
    main()
