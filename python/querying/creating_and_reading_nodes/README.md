
# Creating and reading nodes with Memgraph Example 

This example demonstrates how to use read and write queries via the `gqlalchemy` Python client.


## 🧠 What This Example Does

The script performs the following actions:

1. **Connects to a running Memgraph instance** using `gqlalchemy`.
2. **Creates an `Person` node** — creating a node with multiple properties.
3. **Execute query** - showcasing how to run write queries
4. **Creates a read query and executes read query** showcasing how to read data from Memgraph.
5. **Showcasing manipulation over Node object**:
   - How to access labels.
   - How to access properties.
   - How to access specific property.


## 🚀 How to Run Memgraph with Docker

To run Memgraph Community using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph:3.2
```


## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include:

```
gqlalchemy
```


## 🧪 How to Run the Script

Once Memgraph is running:

```bash
python3 creating_and_reading_nodes.py
```


## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph v3.2**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!


## 🏢 Enterprise or Community?

This example works with **Memgraph Community Edition** 
