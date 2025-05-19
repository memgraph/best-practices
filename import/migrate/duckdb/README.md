# DuckDB

With the `migrate.duckdb()` procedure, users can connect to the **DuckDB**
database and query various data sources.

## Prerequisites

Install the required libraries from the `duckdb` folder:

```bash
pip install -r requirements.txt
```

## Quick start

To test the usage, first start Memgraph MAGE:

```bash
docker run -p 7687:7687 memgraph/memgraph-mage
```

Then, copy the provided [users.csv](./data/users.csv) file to the running
container. To do that, find out the container ID by running in terminal:

```bash
docker ps
```

Next, copy the file:

```bash
docker cp users.csv <container_id>:/usr/lib/memgraph/users.csv
```

Then, start the client:

```bash
python client.py
```

The client script connects to the local Memgraph instance and runs
`migrate.duckdb()` procedure which runs DuckDB with the in-memory mode, without
any persistence and is used just to proxy to the underlying data sources. The
procedure streams results from DuckDB to Memgraph where it will create nodes.