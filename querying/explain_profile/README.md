# Memgraph EXPLAIN and PROFILE Example

This example demonstrates how to use the **EXPLAIN** and **PROFILE** clauses in Memgraph to analyze query execution plans and performance using the `gqlalchemy` Python client.

---

## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using `gqlalchemy`.
2. **Switches Memgraph into analytical mode** (`STORAGE MODE IN_MEMORY_ANALYTICAL`).
3. **Drops the existing graph** to start from a clean state.
4. **Reads and executes Cypher queries** from the energy management system dataset.
5. **Demonstrates EXPLAIN and PROFILE clauses** with various query examples:
   - Simple MATCH query on generators
   - Complex query with multiple operations on the power grid
   - Query using indexes on generator IDs
   - Comparison between EXPLAIN and PROFILE outputs

Each example also **measures and prints** the query execution time.

---

## 🚀 How to Run Memgraph with Docker

To run Memgraph Enterprise using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph-mage:3.2
```

## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Or directly:

```bash
pip install gqlalchemy==1.7.0
```

---

## 🧪 How to Run the Script

Once Memgraph is running:

```bash
python3 querying/explain_profile/explain_profile.py
```

The script will automatically use the energy management system dataset from `datasets/energy-management-memgraph-lab/energy-management-system.cypherl`.

---

## 📊 Understanding EXPLAIN vs PROFILE

- **EXPLAIN**: Shows the query execution plan without actually running the query. Useful for understanding how Memgraph will process your query.
- **PROFILE**: Executes the query and shows detailed statistics about the execution, including:
  - Number of rows processed
  - Time spent in each operation
  - Memory usage
  - Actual vs. estimated rows

---

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph MAGE v3.2**
- **gqlalchemy v1.7.0**

---

## 💬 Need Help?

If you run into issues or have questions, reach out on the [Memgraph Discord server](https://discord.gg/memgraph) — we're happy to help!

## 🏢 Enterprise or Community?

> 🛑 This example **uses Memgraph Community Version**. 