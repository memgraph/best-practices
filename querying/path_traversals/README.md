# Memgraph Path Traversal Example

This example demonstrates how to **ingest a graph into Memgraph** from a `.cypherl` file and **perform different path traversal algorithms** using the `gqlalchemy` Python client.

---

## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using `gqlalchemy`.
2. **Switches Memgraph into analytical mode** (`STORAGE MODE IN_MEMORY_ANALYTICAL`).
3. **Drops the existing graph** to start from a clean state.
4. **Reads and executes Cypher queries** from a `.cypherl` file (one query per line).
5. **Performs multiple path-finding queries**:
   - Shortest path (`wShortest`) between two nodes.
   - Depth-First Search (DFS) for finding all paths up to a specific depth.
   - Breadth-First Search (BFS) for efficiently finding reachable nodes.
   - BFS with **inline filtering** during traversal.
   - Shortest path using **custom cost functions**.

Each path traversal example also **measures and prints** the query execution time.

---

## 🚀 How to Run Memgraph with Docker

## 🚀 How to Run Memgraph with Docker

To run Memgraph Enterprise using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph-mage:3.2
```

## 🛠 Requirements

Install dependencies with:

```bash
pip install gqlalchemy
```

Or if you have a `requirements.txt`, it should include:

```
gqlalchemy
```

---

## 🧪 How to Run the Script

Once Memgraph is running:

```bash
python3 path_traversals.py path/to/energy-management-system.cypherl
```

Dataset is included in the `datasets/` base directory

---

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph MAGE v3.2**
- **gqlalchemy v1.7.0+**

---

## 💬 Need Help?

If you run into issues or have questions, reach out on the [Memgraph Discord server](https://discord.gg/memgraph) — we’re happy to help!

## 🏢 Enterprise or Community?

> 🛑 This example **uses Memgraph Community Version**.
