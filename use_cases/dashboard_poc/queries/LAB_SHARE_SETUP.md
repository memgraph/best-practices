# Setting Up Parameterized Query Shares in Memgraph Lab

> **Prerequisite**: Memgraph Enterprise license is required for query sharing.  
> Set `MG_ENTERPRISE_LICENSE` and `MG_ORGANIZATION_NAME` in your `.env` file.

## Overview

The web app uses Memgraph Lab's **query sharing** feature to open parameterized
queries with graph visualization. Each query gets a unique `shareId` that the
web app uses to construct URLs like:

```
http://localhost:3000?shareId=<ID>&shareParams=acct_num:<value>
```

When a user enters an account number and clicks "Lab Graph", the app opens Lab
with the query pre-filled and the parameter substituted.

---

## Step-by-Step Setup

### 1. Open Memgraph Lab

Navigate to [http://localhost:3000](http://localhost:3000) and connect to the
main Memgraph instance (should auto-connect via Quick Connect).

### 2. Create Each Query Share

Repeat the following for each of the 4 queries below:

1. **Paste the query** into the query editor
2. **Open the Parameters panel** (click the `{ }` icon or "Parameters" tab)
3. **Add parameter**: `acct_num` = `"9968748174"` (use any valid fraud account)
4. **Run the query** to verify it works
5. **Switch to Graph view** to see the visual output
6. **Click the Share button** (top-right area of the query editor)
7. **Select "Graph" view** as the default display
8. **Copy the shareId** from the generated URL

### 3. Enter Share IDs in the Web App

Open the web app at [http://localhost:5000](http://localhost:5000), click
**"Share IDs"** in the navbar, and paste each shareId into the corresponding field.

---

## The 4 Parameterized Queries

### Query 1: Money In (30 days)

```cypher
WITH datetime() - duration('P30D') AS rangeStart,
     datetime() AS rangeEnd
MATCH p = (a:Account)-[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
WHERE t.txn_timestamp >= rangeStart
  AND t.txn_timestamp < rangeEnd
RETURN p;
```

**Parameter**: `acct_num` = `"9968748174"`  
**View**: Graph

---

### Query 2: Money Out (30 days)

```cypher
WITH datetime() - duration('P30D') AS rangeStart,
     datetime() AS rangeEnd
MATCH p = (a:Account {acct_num: $acct_num})-[t:TRANSFER_TO]->(b:Account)
WHERE t.txn_timestamp >= rangeStart
  AND t.txn_timestamp < rangeEnd
RETURN p;
```

**Parameter**: `acct_num` = `"9968748174"`  
**View**: Graph

---

### Query 3: Fraud Upstream

```cypher
MATCH p = (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
            -[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
RETURN p;
```

**Parameter**: `acct_num` = `"9968748174"`  
**View**: Graph

---

### Query 4: 2-Hop Fraud Neighborhood (last 7 days)

```cypher
WITH datetime() - duration('P7D') AS since
MATCH (target:Account {acct_num: $acct_num})-[f:TRANSFER_TO {fraud: true}]-()
WHERE f.fraud_date_identified >= since
WITH DISTINCT target
MATCH p = (n:Account)-[:TRANSFER_TO*1..2]->(target)
RETURN p
UNION
WITH datetime() - duration('P7D') AS since
MATCH (target:Account {acct_num: $acct_num})-[f:TRANSFER_TO {fraud: true}]-()
WHERE f.fraud_date_identified >= since
WITH DISTINCT target
MATCH p = (target)-[:TRANSFER_TO*1..2]->(m:Account)
RETURN p;
```

**Parameter**: `acct_num` = `"4030419178"`  
**View**: Graph

> **Logic**:
> 1. **Gate**: Checks that the central account has at least one fraud transfer
>    (incoming **or** outgoing) with `fraud_date_identified` in the last 7 days.
> 2. **Expand**: Gets the full 2-hop neighborhood (all paths 1..2 hops before
>    AND after the central node). No time filter on the expansion itself --
>    the fraud gate scopes relevance, the 2-hop expansion shows the network.

---

## How the URL Works

When Lab creates a share, it stores the query + GSS + parameters in remote
storage (the `memgraph-storage` service) and generates a `shareId`.

The web app constructs URLs like:

```
http://localhost:3000?shareId=abc123-def456&shareParams=acct_num:9968748174
```

- `shareId` — identifies the stored query/GSS/params
- `shareParams` — overrides the parameter value (format: `paramName:value`)

This means Lab will load the original query but substitute `$acct_num` with
the value provided in the URL. The graph renders automatically.

---

## Important: Fraud is on Relationships

The `fraud` property lives on **TRANSFER_TO relationships**, not on Account nodes.
Accounts have `is_sabric_scam` and `is_scam_acct` flags to indicate involvement
in fraud patterns, but `fraud: true` is only on the relationship/transaction.

## Sample Accounts for Testing

Use accounts involved in fraud transfers (from the ingested data):

- `9968748174`
- `7667246713`
- `1753525439`
- `7642155465`
- `0258808467`
