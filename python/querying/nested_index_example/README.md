# Nested Index Query Performance Example with Memgraph

This example demonstrates how to use GQLAlchemy to showcase the performance impact of nested indexes in Memgraph.

## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using `gqlalchemy`.
2. **Creates 2000 `Person` nodes** with a nested `address` property.
3. **Executes a query** to find people by a nested property (country) and times the query execution.
4. **Creates a nested index** on `:Person(address.country)`.
5. **Executes the same query again** and times the execution to show the performance improvement.

## 🚀 How to Run Memgraph with Docker

To run Memgraph Community using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph:3.3
```

## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include:

```
GQLAlchemy==1.7.0
```

## 🧪 How to Run the Script

Once Memgraph is running:

```bash
python3 nested_index_example.py
```

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph v3.3**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!

## 🏢 Enterprise or Community?

This example works with **Memgraph Community Edition** 