#!/usr/bin/env python3
"""
ABSA PoC – Web App for Memgraph fraud detection.

Provides:
  • A search form to enter an account number
  • Direct query execution against Memgraph (via GQLAlchemy)
  • In-app graph visualization using Memgraph Orb library
  • Buttons that open Memgraph Lab with parameterized query shares (graph view)
  • A settings page to configure query share IDs

Set environment variables or edit the config below:
  MEMGRAPH_HOST  – Memgraph Bolt host  (default: 127.0.0.1)
  MEMGRAPH_PORT  – Memgraph Bolt port  (default: 7687)
  LAB_URL        – Memgraph Lab base URL (default: http://localhost:3000)
"""

import os
import json
import traceback
from datetime import datetime, timezone

from flask import Flask, render_template, request, jsonify, redirect, url_for
from gqlalchemy import Memgraph

# ── Configuration ───────────────────────────────────────────────────
MEMGRAPH_HOST = os.getenv("MEMGRAPH_HOST", "127.0.0.1")
MEMGRAPH_PORT = int(os.getenv("MEMGRAPH_PORT", "7687"))
LAB_URL = os.getenv("LAB_URL", "http://localhost:3000")

app = Flask(__name__)
db = None

# ── Parameterized Query Definitions ─────────────────────────────────
# These are the 4 queries that can be shared via Memgraph Lab.
# Each has a Cypher query using $acct_num parameter.
# The "lab_query" version returns paths (p) for graph rendering in Lab.
# The "table_query" version returns tabular data for the web app.
PARAM_QUERIES = {
    "money_in": {
        "title": "Money In (30 days)",
        "description": "All transfers TO this account in the last 30 days",
        "icon": "bi-box-arrow-in-down",
        "color": "success",
        "lab_query": """WITH datetime() - duration('P30D') AS rangeStart,
     datetime() AS rangeEnd
MATCH p = (a:Account)-[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
WHERE t.txn_timestamp >= rangeStart
  AND t.txn_timestamp < rangeEnd
RETURN p;""",
        "table_query": """
            WITH datetime() - duration('P30D') AS rangeStart,
                 datetime() AS rangeEnd
            MATCH (a:Account)-[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
            WHERE t.txn_timestamp >= rangeStart
              AND t.txn_timestamp < rangeEnd
            RETURN a.acct_num AS Source_Acc,
                   b.acct_num AS Target_Acc,
                   t.txn_type AS Txn_Type,
                   t.txn_amt AS Amount,
                   toString(t.txn_timestamp) AS Timestamp,
                   a.bank AS Source_Bank,
                   t.channel_desc AS Channel,
                   t.fraud AS Is_Fraud
            ORDER BY t.txn_timestamp DESC
            LIMIT 200;
        """,
    },
    "money_out": {
        "title": "Money Out (30 days)",
        "description": "All transfers FROM this account in the last 30 days",
        "icon": "bi-box-arrow-up",
        "color": "warning",
        "lab_query": """WITH datetime() - duration('P30D') AS rangeStart,
     datetime() AS rangeEnd
MATCH p = (a:Account {acct_num: $acct_num})-[t:TRANSFER_TO]->(b:Account)
WHERE t.txn_timestamp >= rangeStart
  AND t.txn_timestamp < rangeEnd
RETURN p;""",
        "table_query": """
            WITH datetime() - duration('P30D') AS rangeStart,
                 datetime() AS rangeEnd
            MATCH (a:Account {acct_num: $acct_num})-[t:TRANSFER_TO]->(b:Account)
            WHERE t.txn_timestamp >= rangeStart
              AND t.txn_timestamp < rangeEnd
            RETURN a.acct_num AS Source_Acc,
                   b.acct_num AS Target_Acc,
                   t.txn_type AS Txn_Type,
                   t.txn_amt AS Amount,
                   toString(t.txn_timestamp) AS Timestamp,
                   b.bank AS Target_Bank,
                   t.channel_desc AS Channel,
                   t.fraud AS Is_Fraud
            ORDER BY t.txn_timestamp DESC
            LIMIT 200;
        """,
    },
    "fraud_upstream": {
        "title": "Fraud Upstream",
        "description": "Fraud-flagged transfers flowing into this account via intermediary",
        "icon": "bi-exclamation-triangle",
        "color": "danger",
        "lab_query": """MATCH p = (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
            -[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
RETURN p;""",
        "table_query": """
            MATCH (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
                    -[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
            RETURN x.acct_num AS Upstream_Acc,
                   a.acct_num AS Intermediary_Acc,
                   b.acct_num AS Target_Acc,
                   t2.txn_amt AS Fraud_Amount,
                   toString(t2.txn_timestamp) AS Fraud_Timestamp,
                   t.txn_amt AS Transfer_Amount,
                   toString(t.txn_timestamp) AS Transfer_Timestamp
            ORDER BY t2.txn_timestamp DESC
            LIMIT 200;
        """,
    },
    "two_hop": {
        "title": "2-Hop Fraud Neighborhood (7 days)",
        "description": "Full 2-hop neighborhood of an account that has fraud activity in/out (last 7 days)",
        "icon": "bi-diagram-3",
        "color": "info",
        "lab_query": """WITH datetime() - duration('P7D') AS since
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
RETURN p;""",
        "table_query": """
            WITH datetime() - duration('P7D') AS since
            MATCH (target:Account {acct_num: $acct_num})-[f:TRANSFER_TO {fraud: true}]-()
            WHERE f.fraud_date_identified >= since
            WITH DISTINCT target
            MATCH (n:Account)-[:TRANSFER_TO*1..2]->(target)
            WHERE n.acct_num <> $acct_num
            WITH target, COLLECT(DISTINCT n.acct_num) AS accounts_before
            OPTIONAL MATCH (target)-[:TRANSFER_TO*1..2]->(m:Account)
            WHERE m.acct_num <> $acct_num
            RETURN target.acct_num AS account,
                   accounts_before AS accounts_2hop_before,
                   COLLECT(DISTINCT m.acct_num) AS accounts_2hop_after;
        """,
    },
}

# Additional non-parameterized queries
GLOBAL_QUERIES = {
    "account_info": {
        "title": "Account Details",
        "cypher": """
            MATCH (a:Account {acct_num: $acct_num})
            OPTIONAL MATCH (a)-[out:TRANSFER_TO]->()
            WITH a, count(out) AS out_degree
            OPTIONAL MATCH ()-[inc:TRANSFER_TO]->(a)
            RETURN a.acct_num AS acct_num,
                   a.cust_name AS cust_name,
                   a.cust_first_name AS cust_first_name,
                   a.bank AS bank,
                   a.acct_status_code AS status,
                   a.is_sabric_scam AS is_sabric_scam,
                   a.is_scam_acct AS is_scam_acct,
                   a.sector_code AS sector_code,
                   a.customer_key AS customer_key,
                   a.cust_phone_number AS phone,
                   a.sabric_case_num AS sabric_case_num,
                   a.sabric_desc AS sabric_desc,
                   toString(a.acct_open_date) AS open_date,
                   toString(a.acct_close_date) AS close_date,
                   out_degree,
                   count(inc) AS in_degree;
        """,
    },
    "fraud_yesterday": {
        "title": "Yesterday's Fraud Transactions",
        "cypher": """
            WITH datetime() - duration('P1D') AS startOfYesterday,
                 datetime() AS startOfToday
            MATCH (a:Account)-[t:TRANSFER_TO {fraud: true}]->(b:Account)
            WHERE t.txn_timestamp >= startOfYesterday
              AND t.txn_timestamp < startOfToday
            RETURN a.acct_num AS Source_Acc,
                   b.acct_num AS Target_Acc,
                   t.txn_type AS Txn_Type,
                   t.txn_amt AS Amount,
                   toString(t.txn_timestamp) AS Timestamp,
                   b.bank AS Target_Bank
            ORDER BY t.txn_timestamp DESC
            LIMIT 500;
        """,
    },
    "fraud_confirmed_7d": {
        "title": "Fraud Confirmed (last 7 days)",
        "cypher": """
            WITH datetime() - duration('P7D') AS rangeStart,
                 datetime() AS rangeEnd
            MATCH (a:Account)-[t:TRANSFER_TO {fraud: true}]->(b:Account)
            WHERE t.fraud_date_identified >= rangeStart
              AND t.fraud_date_identified < rangeEnd
            RETURN a.acct_num AS Source_Acc,
                   b.acct_num AS Target_Acc,
                   t.txn_type AS Txn_Type,
                   t.txn_amt AS Amount,
                   toString(t.txn_timestamp) AS Txn_Timestamp,
                   toString(t.fraud_date_identified) AS Fraud_Date,
                   t.matched_rule AS Matched_Rule
            ORDER BY t.fraud_date_identified DESC
            LIMIT 500;
        """,
    },
    "phone_clusters": {
        "title": "Phone Bank Clusters",
        "cypher": """
            MATCH (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
                    -[r:TRANSFER_TO]->(b:Account {bank: "phone"})
            WITH b, COUNT(DISTINCT a.acct_num) AS mule_count
            WHERE mule_count >= 2
            RETURN b.acct_num AS Phone_Account,
                   mule_count AS Num_Mules
            ORDER BY mule_count DESC
            LIMIT 100;
        """,
    },
}


# ── Helpers ─────────────────────────────────────────────────────────

def get_db() -> Memgraph:
    """Lazy-connect to Memgraph."""
    global db
    if db is None:
        db = Memgraph(host=MEMGRAPH_HOST, port=MEMGRAPH_PORT)
    return db


def serialize_row(row: dict) -> dict:
    """Convert a result row to JSON-safe types."""
    out = {}
    for k, v in row.items():
        if isinstance(v, (list, tuple)):
            out[k] = [str(item) for item in v]
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _safe_val(v):
    """Convert a value to a JSON-safe type."""
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _extract_graph_elements(val, nodes_map, edges_map, target_acct=None):
    """Recursively extract nodes and edges from a graph value (Path, Node, Relationship)."""
    if val is None:
        return

    # GQLAlchemy Path: has _nodes and _relationships
    if hasattr(val, "_nodes") and hasattr(val, "_relationships"):
        for n in val._nodes:
            _add_node(n, nodes_map, target_acct)
        for r in val._relationships:
            _add_edge(r, edges_map)
        return

    # GQLAlchemy Node: has _id and _labels
    if hasattr(val, "_id") and hasattr(val, "_labels"):
        _add_node(val, nodes_map, target_acct)
        return

    # GQLAlchemy Relationship: has _id and _type
    if hasattr(val, "_id") and hasattr(val, "_type"):
        _add_edge(val, edges_map)
        return


def _add_node(node, nodes_map, target_acct=None):
    """Add a node to the nodes map (dedup by id)."""
    nid = getattr(node, "_id", None)
    if nid is None:
        return
    if nid in nodes_map:
        return

    acct_num = _safe_val(getattr(node, "acct_num", "")) or ""
    nodes_map[nid] = {
        "id": nid,
        "acct_num": acct_num,
        "bank": _safe_val(getattr(node, "bank", "")) or "",
        "cust_name": _safe_val(getattr(node, "cust_name", "")) or "",
        "cust_phone_number": _safe_val(getattr(node, "cust_phone_number", "")) or "",
        "acct_status_code": _safe_val(getattr(node, "acct_status_code", "")) or "",
        "sector_code": _safe_val(getattr(node, "sector_code", "")) or "",
        "customer_key": _safe_val(getattr(node, "customer_key", "")) or "",
        "acct_open_date": _safe_val(getattr(node, "acct_open_date", None)),
        "is_sabric_scam": bool(getattr(node, "is_sabric_scam", False)),
        "is_scam_acct": bool(getattr(node, "is_scam_acct", False)),
        "sabric_case_num": _safe_val(getattr(node, "sabric_case_num", "")) or "",
        "sabric_desc": _safe_val(getattr(node, "sabric_desc", "")) or "",
        "is_target": (str(acct_num) == str(target_acct)) if target_acct else False,
    }


def _add_edge(rel, edges_map):
    """Add an edge to the edges map (dedup by id)."""
    rid = getattr(rel, "_id", None)
    if rid is None:
        return
    if rid in edges_map:
        return

    edges_map[rid] = {
        "id": rid,
        "start": getattr(rel, "_start_node_id", None),
        "end": getattr(rel, "_end_node_id", None),
        "label": getattr(rel, "_type", "TRANSFER_TO"),
        "fraud": bool(getattr(rel, "fraud", False)),
        "txn_id": _safe_val(getattr(rel, "txn_id", "")) or "",
        "txn_amt": _safe_val(getattr(rel, "txn_amt", None)),
        "txn_type": _safe_val(getattr(rel, "txn_type", "")) or "",
        "txn_type_desc": _safe_val(getattr(rel, "txn_type_desc", "")) or "",
        "channel": _safe_val(getattr(rel, "channel", "")) or "",
        "channel_desc": _safe_val(getattr(rel, "channel_desc", "")) or "",
        "timestamp": _safe_val(getattr(rel, "txn_timestamp", None)),
        "fraud_date_identified": _safe_val(getattr(rel, "fraud_date_identified", None)),
        "matched_rule": _safe_val(getattr(rel, "matched_rule", "")) or "",
        "dbt_acct_num": _safe_val(getattr(rel, "dbt_acct_num", "")) or "",
        "crd_acct_num": _safe_val(getattr(rel, "crd_acct_num", "")) or "",
    }


# ── Routes ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    """Main page."""
    return render_template(
        "index.html",
        lab_url=LAB_URL,
        param_queries={k: {
            "title": v["title"],
            "description": v["description"],
            "icon": v["icon"],
            "color": v["color"],
            "lab_query": v["lab_query"],
        } for k, v in PARAM_QUERIES.items()},
    )


@app.route("/api/query/<query_key>")
def run_query(query_key: str):
    """Execute a named query and return JSON results."""
    acct_num = request.args.get("acct_num", "").strip()

    # Check parameterized queries first, then global
    if query_key in PARAM_QUERIES:
        query_def = PARAM_QUERIES[query_key]
        cypher = query_def["table_query"]
        title = query_def["title"]
        description = query_def["description"]
    elif query_key in GLOBAL_QUERIES:
        query_def = GLOBAL_QUERIES[query_key]
        cypher = query_def["cypher"]
        title = query_def["title"]
        description = query_def.get("description", "")
    else:
        return jsonify({"error": f"Unknown query: {query_key}"}), 404

    try:
        conn = get_db()
        params = {"acct_num": acct_num} if acct_num else {}
        results = list(conn.execute_and_fetch(cypher, params))
        rows = [serialize_row(r) for r in results]
        return jsonify({
            "title": title,
            "description": description,
            "row_count": len(rows),
            "rows": rows,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/graph/<query_key>")
def graph_query(query_key: str):
    """Execute the graph (path-returning) query and return nodes + edges for Orb."""
    acct_num = request.args.get("acct_num", "").strip()

    if query_key not in PARAM_QUERIES:
        return jsonify({"error": f"Unknown query: {query_key}"}), 404
    if not acct_num:
        return jsonify({"error": "Account number is required"}), 400

    query_def = PARAM_QUERIES[query_key]
    cypher = query_def["lab_query"]

    try:
        conn = get_db()
        results = list(conn.execute_and_fetch(cypher, {"acct_num": acct_num}))

        nodes_map = {}
        edges_map = {}
        for row in results:
            for val in row.values():
                _extract_graph_elements(val, nodes_map, edges_map, acct_num)

        return jsonify({
            "title": query_def["title"],
            "nodes": list(nodes_map.values()),
            "edges": list(edges_map.values()),
            "node_count": len(nodes_map),
            "edge_count": len(edges_map),
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def stats():
    """Return basic graph statistics."""
    try:
        conn = get_db()
        stat_queries = {
            "total_accounts": "MATCH (a:Account) RETURN count(a) AS cnt;",
            "total_transfers": "MATCH ()-[r:TRANSFER_TO]->() RETURN count(r) AS cnt;",
            "fraud_transfers": "MATCH ()-[r:TRANSFER_TO {fraud: true}]->() RETURN count(r) AS cnt;",
        }
        result = {}
        for key, q in stat_queries.items():
            rows = list(conn.execute_and_fetch(q))
            result[key] = rows[0]["cnt"] if rows else 0
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/sample-fraud-accounts")
def sample_fraud_accounts():
    """Return sample accounts involved in fraud transfers for quick testing."""
    try:
        conn = get_db()
        results = list(conn.execute_and_fetch(
            """MATCH (a:Account)-[r:TRANSFER_TO {fraud: true}]->()
               RETURN DISTINCT a.acct_num AS acct_num LIMIT 10;"""
        ))
        return jsonify({"accounts": [r["acct_num"] for r in results]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Main ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
