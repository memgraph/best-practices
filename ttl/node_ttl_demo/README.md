# ⏳ Node TTL with Memgraph Example

This example demonstrates how to use **Node TTL (Time-to-Live)** inside Memgraph with the `gqlalchemy` Python client.

## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using `gqlalchemy`.
2. **Enables the TTL background job** to activate automatic deletion of expired nodes.
3. **Executes a write query** to create a node with a `ttl` property.
4. **Reads data from Memgraph** immediately after the node is created.
5. **Waits a few seconds for the TTL to expire**, then queries again to confirm the node is deleted.

## 🚀 How to Run Memgraph with Docker

To run Memgraph Enterprise using Docker:

```bash
docker run -it --rm -p 7687:7687 -e MEMGRAPH_ORGANIZATION_NAME=<YOUR_ORG_NAME> -e MEMGRAPH_ENTERPRISE_LICENSE=<YOUR_ENTERPRISE_LICENSE> memgraph/memgraph:3.2.0
```
## 🛠 Requirements

Install Python dependencies using:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include:

```
gqlalchemy
```

## 🧪 How to Run the Script

Make sure Memgraph is running, then execute:

```bash
python3 node_ttl_demo.py
```

## 🧼 TTL Behavior

The script sets a node to expire after a few seconds using the `ttl` Cypher clause. Memgraph's TTL background job ensures expired nodes are deleted without manual intervention.

## 🔖 Version Compatibility

This example was tested with:

* **Memgraph v3.2**
* **GQLAlchemy v1.11.0+**

If you're using another version and encounter issues, feel free to ask for help on the [Memgraph Discord server](https://discord.gg/memgraph)!

## 🏢 Enterprise or Community?

This example requires **Memgraph Enterprise Edition**.
