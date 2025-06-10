# 🔁 Migrate data from Neo4j to Memgraph using migrate module

This example demonstrates how to **migrate nodes** from a **Neo4j 5.26** instance to **Memgraph 3.2.1 (Community Edition)** using the `gqlalchemy` Python client and Memgraph’s built-in **`migrate.neo4j`** module.

## 🧠 What This Example Does

The script performs the following actions:

1. **Ensures Neo4j has data**: it inserts up to **50 million `Person` nodes** with `id` and `message` properties.
2. **Starts two parallel workers** using the `multiprocessing` module:

   * One **executes the migration** via Memgraph's `CALL migrate.neo4j(...)` procedure.
   * The other **monitors Memgraph’s storage state**, logging the number of vertices and memory usage using `SHOW STORAGE INFO`.
3. **Indexes** are created on the `Person(id)` node to speed up access and deduplication during merge.

## 🚀 How to Run with Docker Compose

You can spin up Neo4j and Memgraph using the Docker Compose file

To start both:

```bash
docker-compose up -d
```

## 🛠 Requirements

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## 🧪 How to Run the Script

Once both Neo4j and Memgraph are up and running:

```bash
python migrate_from_neo4j.py
```

## 🧼 Migration Behavior

* The script inserts `Person` nodes into Neo4j if fewer than 50M exist.
* Then it sets **Memgraph’s storage mode** to `IN_MEMORY_ANALYTICAL`, clears the current graph, creates indexes, and executes a `CALL migrate.neo4j(...)` query to transfer data.
* Meanwhile, another process monitors `SHOW STORAGE INFO` output from Memgraph in real time.

## 🧾 Sample Node Data

Each `Person` node in Neo4j has the following structure:

```json
{
  "id": 123456,
  "message": "A long random string..."
}
```

## 🔖 Version Compatibility

This example was tested with:

* **Neo4j 5.26 (Enterprise, no auth)**
* **Memgraph 3.2.1 (Community)**
* **GQLAlchemy v1.11+**

> Note: Memgraph’s `migrate` module is available in the **Community Edition** and does not require a commercial license.

## 💬 Need Help?

If you encounter issues, visit the [Memgraph Discord server](https://discord.gg/memgraph) to get help from the community or the Memgraph team!

