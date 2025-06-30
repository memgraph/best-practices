# GraphQL with Memgraph Example

This example demonstrates how to use GraphQL with Memgraph, including data ingestion using GQLAlchemy and querying using the GraphQL API.

## 🧠 What This Example Does

The example consists of two main scripts:

1. **Data Ingestion (`ingest_data.py`)**:
   - Connects to a running Memgraph instance using `gqlalchemy`
   - Creates sample data for an energy management system
   - Creates nodes for buildings, devices, meters, and readings
   - Establishes relationships between nodes

2. **GraphQL Queries (`query_graphql.py`)**:
   - Connects to the GraphQL server
   - Executes queries to fetch buildings with their devices and meters
   - Retrieves devices with their readings
   - Creates new buildings using mutations

## 🚀 How to Run Memgraph with Docker

To run Memgraph Community using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph:3.2 --bolt-server-name-for-init=Neo4j/5.2.0 --query-callable-mappings-path=/etc/memgraph/apoc_compatibility_mappings.json
```

`--query-callable-mappings-path` is the necessary flag to bind apoc procedures to compatible MAGE query modules

## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` includes:
```
gqlalchemy==1.7.0
requests==2.31.0
python-dotenv==1.0.0
```

## 🧪 How to Run the Scripts

1. First, start the GraphQL server:
```bash
cd src
npm install
node index.js
```

2. In a new terminal, ingest the sample data:
```bash
python3 ingest_data.py
```

3. Query the data using GraphQL:
```bash
python3 query_graphql.py
```

## 🔖 Version Compatibility

This example was built and tested with:
- **Memgraph v3.4**
- **Node.js v14 or higher**
- **Python 3.8 or higher**

## 🏢 Enterprise or Community?

This example works with **Memgraph Community Edition**

## 🤝 Need Help?

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help! 
