// =====================================================================
// ABSA PoC – Cypher Query Library
// Schema:  (:Account)-[:TRANSFER_TO]->(:Account)
// =====================================================================


// ─────────────────────────────────────────────────────────────────────
// 1. Yesterday's transactions marked as fraud
// ─────────────────────────────────────────────────────────────────────
WITH
  datetime() - duration('P1D') AS startOfYesterday,
  datetime() AS startOfToday
MATCH p = (a:Account)-[t:TRANSFER_TO {fraud: true}]->(b:Account)
WHERE t.txn_timestamp >= startOfYesterday
  AND t.txn_timestamp < startOfToday
RETURN a.acct_num AS Source_Acc, b.acct_num AS Target_Acc,
       t.txn_type, b.bank, p;


// ─────────────────────────────────────────────────────────────────────
// 2. Transactions confirmed as fraud in last 7 days (Memgraph DB)
// ─────────────────────────────────────────────────────────────────────
WITH
  datetime() - duration('P7D') AS startOfYesterday,
  datetime() AS startOfToday
MATCH p = (a:Account)-[t:TRANSFER_TO {fraud: true}]->(b:Account)
WHERE t.fraud_date_identified >= startOfYesterday
  AND t.fraud_date_identified < startOfToday
RETURN p, startOfYesterday, startOfToday;


// ─────────────────────────────────────────────────────────────────────
// 3. Transactions confirmed as fraud yesterday – with 2nd hop
//    (downstream beneficiary must have customer_key)
// ─────────────────────────────────────────────────────────────────────
WITH
  datetime() - duration('P1D') AS startOfYesterday,
  datetime() AS startOfToday
MATCH p = (a:Account)-[t:TRANSFER_TO {fraud: true}]->(b:Account)
            -[r:TRANSFER_TO]->(x:Account)
WHERE t.fraud_date_identified >= startOfYesterday
  AND t.fraud_date_identified < startOfToday
  AND x.customer_key IS NOT NULL
RETURN p, startOfYesterday, startOfToday;


// ─────────────────────────────────────────────────────────────────────
// 4. Transactions confirmed as fraud in last 7 days – with 2nd hop
// ─────────────────────────────────────────────────────────────────────
WITH
  datetime() - duration('P7D') AS startOfYesterday,
  datetime() AS startOfToday
MATCH p = (a:Account)-[t:TRANSFER_TO {fraud: true}]->(b:Account)
            -[r:TRANSFER_TO]->(X:Account)
WHERE t.fraud_date_identified >= startOfYesterday
  AND t.fraud_date_identified < startOfToday
RETURN p, startOfYesterday, startOfToday;


// ─────────────────────────────────────────────────────────────────────
// 5. Money In – all transfers TO a specific account (last 30 days)
//    Parameterized: $acct_num
//
//    ▶ LAB SHARE QUERY (paste this into Lab's query editor):
//    ┌─────────────────────────────────────────────────────────────────
//    │ WITH datetime() - duration('P30D') AS rangeStart,
//    │      datetime() AS rangeEnd
//    │ MATCH p = (a:Account)-[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
//    │ WHERE t.txn_timestamp >= rangeStart
//    │   AND t.txn_timestamp < rangeEnd
//    │ RETURN p;
//    └─────────────────────────────────────────────────────────────────
//    Parameters panel:  acct_num = "9968748174"
//    Share view: Graph
// ─────────────────────────────────────────────────────────────────────
WITH
  datetime() - duration('P30D') AS startOfYesterday,
  datetime() AS startOfToday
MATCH p = (a:Account)-[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
WHERE t.txn_timestamp >= startOfYesterday
  AND t.txn_timestamp < startOfToday
RETURN a.acct_num AS Source_Acc, b.acct_num AS Target_Acc,
       t.txn_type, a.bank, p;


// ─────────────────────────────────────────────────────────────────────
// 6. Money Out – all transfers FROM a specific account (last 30 days)
//    Parameterized: $acct_num
//
//    ▶ LAB SHARE QUERY (paste this into Lab's query editor):
//    ┌─────────────────────────────────────────────────────────────────
//    │ WITH datetime() - duration('P30D') AS rangeStart,
//    │      datetime() AS rangeEnd
//    │ MATCH p = (a:Account {acct_num: $acct_num})-[t:TRANSFER_TO]->(b:Account)
//    │ WHERE t.txn_timestamp >= rangeStart
//    │   AND t.txn_timestamp < rangeEnd
//    │ RETURN p;
//    └─────────────────────────────────────────────────────────────────
//    Parameters panel:  acct_num = "9968748174"
//    Share view: Graph
// ─────────────────────────────────────────────────────────────────────
WITH
  datetime() - duration('P30D') AS startOfYesterday,
  datetime() AS startOfToday
MATCH p = (a:Account {acct_num: $acct_num})-[t:TRANSFER_TO]->(b:Account)
WHERE t.txn_timestamp >= startOfYesterday
  AND t.txn_timestamp < startOfToday
RETURN a.acct_num AS Source_Acc, b.acct_num AS Target_Acc,
       t.txn_type, b.bank, p;


// ─────────────────────────────────────────────────────────────────────
// 7. Fraud transfers into a specific account (with upstream path)
//    Parameterized: $acct_num
//
//    ▶ LAB SHARE QUERY (paste this into Lab's query editor):
//    ┌─────────────────────────────────────────────────────────────────
//    │ MATCH p = (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
//    │             -[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
//    │ RETURN p;
//    └─────────────────────────────────────────────────────────────────
//    Parameters panel:  acct_num = "9968748174"
//    Share view: Graph
// ─────────────────────────────────────────────────────────────────────
MATCH p = (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
            -[t:TRANSFER_TO]->(b:Account {acct_num: $acct_num})
RETURN p;


// ─────────────────────────────────────────────────────────────────────
// 8. Phone number clusters with at least X confirmed mules
//    (accounts receiving fraud-flagged transfers and forwarding
//     to phone-bank accounts)
// ─────────────────────────────────────────────────────────────────────
MATCH p = (x:Account)-[t2:TRANSFER_TO {fraud: true}]->(a:Account)
            -[r:TRANSFER_TO]->(b:Account {bank: "phone"})
WITH b, COUNT(DISTINCT a.acct_num) AS in_degree, COLLECT(p) AS paths
WHERE in_degree >= 2
UNWIND paths AS p
RETURN b.acct_num, p;


// ─────────────────────────────────────────────────────────────────────
// 9. One device used by more than one mule (Aggregated DB)
//    NOTE: Requires :Device nodes and :USES_DEVICE relationships
//          (not part of the base Account/TRANSFER_TO schema)
// ─────────────────────────────────────────────────────────────────────
// WITH
//   datetime() - duration('P1D') AS startOfYesterday,
//   datetime() AS startOfToday
// MATCH p = (a:Account)-[t:TRANSFER_TO {contains_fraud: true}]->(b:Account)
//             -[u:USES_DEVICE]-(d:Device)
// WITH d, COUNT(DISTINCT b.acct_num) AS in_degree, COLLECT(p) AS paths
// WHERE t.txn_timestamp >= startOfYesterday
//   AND t.txn_timestamp < startOfToday
//   AND in_degree >= 2
// UNWIND paths AS p
// RETURN p, d.device_id;


// ─────────────────────────────────────────────────────────────────────
// 10. 2-Hop Fraud Neighborhood (last 7 days)
//
//     Logic:
//       1. GATE: the central account ($acct_num) must have at least one
//          fraud transfer (incoming OR outgoing, direction-agnostic)
//          with fraud_date_identified in the last 7 days.
//       2. EXPAND: once confirmed, get the full 2-hop neighborhood
//          (all paths 1..2 hops before AND after the central node).
//          No additional time filter on the expansion — the fraud gate
//          scopes relevance; the 2-hop expansion shows the full network.
//
//     Parameterized: $acct_num
// ─────────────────────────────────────────────────────────────────────

// 10a. Full 2-hop fraud neighbourhood (tabular: before + after)
WITH datetime() - duration('P7D') AS since
MATCH (target:Account {acct_num: $acct_num})-[f:TRANSFER_TO {fraud: true}]-()
WHERE f.fraud_date_identified >= since
WITH DISTINCT target
MATCH (n:Account)-[:TRANSFER_TO*1..2]->(target)
WHERE n.acct_num <> $acct_num
WITH target, COLLECT(DISTINCT n.acct_num) AS accounts_before
OPTIONAL MATCH (target)-[:TRANSFER_TO*1..2]->(m:Account)
WHERE m.acct_num <> $acct_num
RETURN target.acct_num AS target_account,
       accounts_before,
       COLLECT(DISTINCT m.acct_num) AS accounts_after;


// 10b. 2-hop fraud visual path exploration (graph rendering)
//
//    ▶ LAB SHARE QUERY (paste this into Lab's query editor):
//    ┌─────────────────────────────────────────────────────────────────
//    │ WITH datetime() - duration('P7D') AS since
//    │ MATCH (target:Account {acct_num: $acct_num})-[f:TRANSFER_TO {fraud: true}]-()
//    │ WHERE f.fraud_date_identified >= since
//    │ WITH DISTINCT target
//    │ MATCH p = (n:Account)-[:TRANSFER_TO*1..2]->(target)
//    │ RETURN p
//    │ UNION
//    │ WITH datetime() - duration('P7D') AS since
//    │ MATCH (target:Account {acct_num: $acct_num})-[f:TRANSFER_TO {fraud: true}]-()
//    │ WHERE f.fraud_date_identified >= since
//    │ WITH DISTINCT target
//    │ MATCH p = (target)-[:TRANSFER_TO*1..2]->(m:Account)
//    │ RETURN p;
//    └─────────────────────────────────────────────────────────────────
//    Parameters panel:  acct_num = "4030419178"
//    Share view: Graph
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
