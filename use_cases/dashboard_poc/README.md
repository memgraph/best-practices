# ABSA Fraud Detection – Graph PoC

A proof-of-concept fraud detection system built on **Memgraph** (graph database), using a synthetic dataset of 200K accounts and 2M transfer relationships. Includes a Flask web app that integrates with Memgraph Lab's **parameterized query sharing** mechanism.

## Architecture

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Web App        │     │  Memgraph MAGE   │     │  Memgraph Lab    │
│   (Flask:5000)   │────▶│  (Bolt:7687)     │◀────│  (HTTP:3000)     │
└──────────────────┘     └──────────────────┘     └──────────────────┘
                                                          │
                                                   ┌──────┴───────┐
                                                   │ Memgraph     │
                                                   │ Storage:7688 │
                                                   │ (Lab shares) │
                                                   └──────────────┘
```

## Graph Schema

```
(:Account)-[:TRANSFER_TO]->(:Account)
```

**Account node properties:**
`acct_num`, `acct_close_date`, `acct_open_date`, `acct_status_code`, `bank`,
`company_registration_no`, `cust_employer_addr_line_1`, `cust_id_number`,
`cust_name`, `cust_phone_number`, `cust_physical_addr_line_1`, `customer_key`,
`fchia521`, `forea521`, `is_crypto_acct`, `is_sabric_scam`, `is_scam_acct`,
`sector_code`, `cust_first_name`, `sabric_case_num`, `sabric_desc`, `sabric_id`, `fraud`

**TRANSFER_TO relationship properties:**
`fraud`, `txn_id`, `txn_amt`, `txn_timestamp`, `dbt_acct_num`, `crd_acct_num`,
`dbt_msg`, `crd_msg`, `channel`, `txn_type`, `channel_desc`, `txn_type_desc`,
`fraud_date_identified`, `txn_sub_type`, `txn_sub_type_desc`, `matched_rule`,
`username`, `txn_sub_sub_type`, `txn_sub_sub_type_desc`

## Dataset

| Entity            | Count       |
|-------------------|-------------|
| Account nodes     | 200,000     |
| Fraud accounts    | 2,000       |
| TRANSFER_TO edges | 2,000,000   |
| Fraud edges       | ~100,000    |

The generator creates realistic fraud patterns:
- **Fraud chains**: `normal → normal → FRAUD → normal → normal` (for 2-hop queries)
- **Phone clusters**: Multiple accounts → fraud intermediary → phone-bank account
- **Recent transactions**: Fraud within last 24h and 7d (for time-based queries)

---

## Quick Start

### 1. Start Infrastructure

```bash
# Copy and configure environment (optional for Enterprise features)
cp .env.example .env
# Edit .env to add your Memgraph Enterprise license if you have one

# Start all services
docker compose up -d
```

Services will be available at:
- **Memgraph Bolt**: `localhost:7687`
- **Memgraph Lab**: `http://localhost:3000`
- **Web App**: `http://localhost:5000`

### 2. Ingest Data

```bash
# Install Python dependencies
pip install -r ingestion/requirements.txt

# Run the data generator and ingestion script
python ingestion/generate_and_ingest.py
```

> **Note:** Ingestion of 200K nodes and 2M relationships takes approximately
> 15–30 minutes depending on hardware. The script shows progress bars.

If Memgraph runs in Docker, the script connects to `localhost:7687` by default.
Override with environment variables:

```bash
MEMGRAPH_HOST=192.168.1.100 MEMGRAPH_PORT=7687 python ingestion/generate_and_ingest.py
```

### 3. Verify Data

After ingestion completes, the script prints verification stats. You can also
check in Memgraph Lab (`http://localhost:3000`):

```cypher
MATCH (a:Account) RETURN count(a);
MATCH (a:Account {fraud: true}) RETURN count(a);
MATCH ()-[r:TRANSFER_TO]->() RETURN count(r);
```

### 4. Use the Web App

Open `http://localhost:5000` and:
1. Enter an account number in the search box
2. Click the account query buttons (Money In, Money Out, Fraud Upstream, 2-Hop)
3. Use the global query buttons for system-wide fraud analysis

---

## Memgraph Lab – Parameterized Query Sharing

The web app integrates with Memgraph Lab's [parameterized query sharing](https://memgraph.com/docs/memgraph-lab/features/sharing-features#create-a-parameterized-query-share-using-query-parameters) feature.

> **Requires**: Memgraph Enterprise license + Lab running in Docker (both configured).

### Setup Steps

1. **Open Memgraph Lab** at `http://localhost:3000`

2. **Create parameterized query shares** in Lab's query editor. For example, create a "Money In" share:

   ```cypher
   // Cypher query:
   WITH datetime() - duration('P30D') AS rangeStart, datetime() AS rangeEnd
   MATCH p = (a:Account)-[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
   WHERE t.txn_timestamp >= rangeStart AND t.txn_timestamp < rangeEnd
   RETURN a.acct_num AS Source_Acc, b.acct_num AS Target_Acc, t.txn_type, a.bank, p;
   
   // Params: { "acct_num": "0000000000" }
   ```

3. **Note the `shareId`** from the generated URL.

4. **Configure the web app** with share IDs via environment variables:

   ```bash
   # In docker-compose.yml or .env
   SHARE_ID_MONEY_IN=<shareId>
   SHARE_ID_MONEY_OUT=<shareId>
   SHARE_ID_FRAUD_UPSTREAM=<shareId>
   SHARE_ID_TWO_HOP=<shareId>
   SHARE_ID_TWO_HOP_VISUAL=<shareId>
   ```

5. **Restart the web app**. The "Open in Memgraph Lab" links will now appear in the account queries panel.

### How It Works

When a user enters an account number and clicks a Lab link, the web app constructs a URL like:

```
http://localhost:3000?shareId=100&shareParams=acct_num:9404936303
```

This opens Memgraph Lab with the pre-configured query, automatically substituting the account number parameter. The query results are visualized as a graph in Lab.

---

## Queries Reference

All queries are in `queries/all_queries.cypher`. Key queries:

| # | Query | Description |
|---|-------|-------------|
| 1 | Yesterday's fraud transactions | Fraud-flagged transfers from the last 24h |
| 2 | Fraud confirmed (7d) | Transfers with `fraud_date_identified` in last 7 days |
| 3 | Fraud + 2nd hop (customer_key) | Fraud with downstream beneficiary having customer_key |
| 4 | Fraud + 2nd hop (7d) | Fraud confirmed in 7d with downstream accounts |
| 5 | Money In | All transfers TO a specific account (30d) |
| 6 | Money Out | All transfers FROM a specific account (30d) |
| 7 | Fraud upstream path | Fraud transfers flowing into a specific account |
| 8 | Phone bank clusters | Phone accounts receiving from 2+ confirmed mules |
| 9 | Device sharing (Aggregated DB) | One device used by multiple mules (requires Device nodes) |
| 10 | 2-Hop neighborhood | Accounts 2 hops before and after a fraud account |

---

## Project Structure

```
absa_poc/
├── docker-compose.yml          # Memgraph MAGE + Lab + Storage + Web App
├── .env.example                # License configuration template
├── ingestion/
│   ├── requirements.txt        # Python dependencies for ingestion
│   └── generate_and_ingest.py  # Data generator + GQLAlchemy ingestion
├── queries/
│   └── all_queries.cypher      # Complete Cypher query library
├── webapp/
│   ├── Dockerfile              # Web app container
│   ├── requirements.txt        # Flask + GQLAlchemy
│   ├── app.py                  # Flask application
│   ├── templates/
│   │   └── index.html          # Main UI template
│   └── static/
│       └── css/
│           └── style.css       # Custom dark theme styles
└── README.md
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMGRAPH_HOST` | `127.0.0.1` | Memgraph Bolt host |
| `MEMGRAPH_PORT` | `7687` | Memgraph Bolt port |
| `LAB_URL` | `http://localhost:3000` | Memgraph Lab base URL |
| `MG_ENTERPRISE_LICENSE` | *(empty)* | Memgraph Enterprise license key |
| `MG_ORGANIZATION_NAME` | *(empty)* | Memgraph organization name |
| `SHARE_ID_MONEY_IN` | *(empty)* | Lab share ID for Money In query |
| `SHARE_ID_MONEY_OUT` | *(empty)* | Lab share ID for Money Out query |
| `SHARE_ID_FRAUD_UPSTREAM` | *(empty)* | Lab share ID for Fraud Upstream query |
| `SHARE_ID_TWO_HOP` | *(empty)* | Lab share ID for 2-Hop query |
| `SHARE_ID_TWO_HOP_VISUAL` | *(empty)* | Lab share ID for 2-Hop Visual query |

### Docker Compose Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| `memgraph` | `memgraph/memgraph-mage` | 7687, 7444 | Main graph database + MAGE algorithms |
| `memgraph-storage` | `memgraph/memgraph` | 7688 | Remote storage for Lab sharing features |
| `memgraph-lab` | `memgraph/lab` | 3000 | Visual query interface |
| `webapp` | Custom (Flask) | 5000 | Parameterized query portal |
