# Power BI Desktop (Windows)

Three ways to connect Power BI Desktop to Memgraph. Make sure you've completed the [Quick Start](README.md#quick-start) first.

---

## Approach 1: Python Script (simplest)

Power BI Desktop can run Python scripts directly as a data source. No middleware needed.

### Steps

1. Configure Python in Power BI: **File > Options > Python scripting** — point it to the venv where `neo4j` and `pandas` are installed
2. Go to **Get Data > Python script**
3. Paste the contents of `direct_query.py`
4. Power BI will detect the DataFrames and offer them as tables:
   - `nodes` — all nodes (persons, companies, products)
   - `edges` — all relationships
   - `person_purchases` — persons with their product purchases (flattened for charts)
   - `company_employees` — companies with employee details
5. Select the tables you want and click **Load**
6. Build your visualizations (e.g. bar chart of total spent per person from `person_purchases`)

**Limitations:** Scheduled refresh requires a Personal Gateway with the same Python environment on a Windows machine.

---

## Approach 2: REST API

Power BI connects to the FastAPI service via the Web connector.

### Steps

1. Start the REST API (see [README.md](README.md#rest-api))
2. In Power BI Desktop, go to **Get Data > Web**
3. Enter the URL: `http://localhost:8000/person-purchases`
4. Power BI will parse the JSON array into a table — click **Load**
5. Repeat for other endpoints as needed (`/nodes`, `/edges`, `/company-employees`)

**Tip:** For scheduled refresh, deploy the API to a server reachable by Power BI Gateway.

---

## Approach 3: ODBC

Use a third-party ODBC driver to connect Power BI directly to Memgraph's Bolt endpoint. No Python or middleware needed.

### Steps

1. Install one of the ODBC drivers:

   | Driver | Type | SQL-to-Cypher |
   |--------|------|---------------|
   | Simba Neo4j ODBC | Commercial | Yes |
   | CData Neo4j ODBC | Commercial | Yes |
   | Devart Neo4j ODBC | Commercial | Yes |

2. Open **Windows ODBC Data Source Administrator** (64-bit)
3. Add a new System DSN with these settings:
   - **Host:** `localhost`
   - **Port:** `7687`
   - **Auth:** No authentication (or empty username/password)
4. In Power BI Desktop, go to **Get Data > ODBC**
5. Select the DSN you created
6. Write SQL queries — the driver translates them to Cypher automatically

**Note:** These drivers are built for Neo4j. Since Memgraph is Bolt-compatible, basic queries work, but some advanced SQL-to-Cypher translations or metadata queries may not be fully compatible. Test thoroughly before relying on this in production.

---

## Comparison

| | Python Script | REST API | ODBC |
|---|---|---|---|
| Setup effort | Low | Medium | Medium |
| Cost | Free | Free | Paid (driver license) |
| Scheduled refresh | Gateway + Python env | Gateway + API server | Gateway + DSN |
| Flexibility | Full Cypher | Pre-built + custom Cypher | SQL (translated to Cypher) |
| Memgraph compatibility | Native | Native | Partial (Bolt-compatible) |
