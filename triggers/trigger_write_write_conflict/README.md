# Write-write conflict with Memgraph triggers demonstration

This example demonstrates how to use **Memgraph triggers** (both `BEFORE COMMIT` and `AFTER COMMIT`) with the Neo4j Python driver (`neo4j`) to simulate real-world data mutation and side-effects using concurrent transactions.

## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using the Neo4j Python driver.
2. **Creates a global node** that serves as the target of trigger-generated relationships.
3. **Creates a `BEFORE COMMIT` trigger** that automatically creates an edge from every newly created node to the global node.
4. **Uses two separate sessions** to simulate concurrent transactions:

   * One modifies the global node in a transaction that remains open.
   * The other creates a node to test whether the trigger can access the global node (it can't if it's uncommitted).
5. **Drops the `BEFORE COMMIT` trigger**, then repeats the same process with an `AFTER COMMIT` trigger.
6. **Validates the behavior** of both trigger types by reading relationships created in the graph.

## 🚀 How to Run Memgraph with Docker

To run Memgraph Enterprise using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph:3.2.0
```

## 🛠 Requirements

Install the required Python dependency with:

```bash
pip install neo4j
```

Your `requirements.txt` should include:

```
neo4j
```

## 🧪 How to Run the Script

Make sure Memgraph is running, then execute:

```bash
python3 memgraph_trigger_demo.py
```

## 🔁 Trigger Behavior

* **BEFORE COMMIT** triggers:

  * Run inside the same transaction that caused the event.
  * Cannot see changes made in uncommitted transactions (i.e., isolation applies).
* **AFTER COMMIT** triggers:

  * Run after the original transaction commits.
  * Can access the full committed graph state.

This script showcases both trigger types and how transaction isolation affects their behavior.

## 📂 File Structure

```
memgraph_trigger_demo.py    # Python script that sets up and tests triggers
requirements.txt            # Python dependencies
README.md                   # This file
```

## 🔖 Version Compatibility

Tested with:

* **Memgraph v3.2**
* **Neo4j Python Driver v5.16.0+**

## 🏢 Enterprise or Community?

This example works with **Memgraph Community Edition**.

## 💬 Need Help?

Reach out to us on the [Memgraph Discord server](https://discord.gg/memgraph) — we’re happy to help!
