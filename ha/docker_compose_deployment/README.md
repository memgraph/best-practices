
# Memgraph HA deployment with docker compose

This example demonstrates how to deploy Memgraph in a high availability mode with docker compose.

The cluster consists of:

- **3 coordinators** (`coord1`/`coord2`/`coord3`) on bolt ports `7691`/`7692`/`7693`
- **3 data instances** (`instance1`/`instance2`/`instance3`) on bolt ports `7687`/`7688`/`7689`

At startup `instance_1` becomes `MAIN` and the others become `REPLICA`s.

## 🚀 How to Run Memgraph with Docker

1. Provide your Memgraph Enterprise license by copying the example env file and
   filling in your organization name and license key:

   ```bash
   cp .env.example .env
   # then edit .env
   ```

2. Start the cluster:

   ```bash
   docker compose up
   ```

## 🔌 Connecting through a coordinator

Clients connect to the cluster through a **coordinator** using the Neo4j driver
with the routing-aware `neo4j://` scheme. The coordinator hands the driver a
routing table, so write transactions go to the current `MAIN` and reads can be
served by `REPLICA`s — and this keeps working across failovers.

The included `connect.py` connects through one coordinator and runs a small
end-to-end sanity check. Dependencies are managed with [uv](https://docs.astral.sh/uv/) —
`uv run` creates the virtual environment and installs the Neo4j driver automatically:

1. `SHOW INSTANCES` on the coordinator and assert the whole cluster (6 instances) is present.
2. Write a node through the coordinator (routed to `MAIN`).
3. Open a direct bolt connection to a `REPLICA` and assert the node replicated.
4. Delete the node through the coordinator.
5. Assert the `REPLICA` is empty again.

```bash
uv run connect.py            # connect through coord1 (default)
uv run connect.py coord2     # connect through coord2
```

> ℹ️ Coordinator management queries such as `SHOW INSTANCES` are not routable, so
> the script opens a plain `bolt://` connection to the coordinator for those,
> and a routed `neo4j://` connection for the data queries.

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph MAGE v3.10.1**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!


## 🏢 Enterprise or Community?

> 🛑 This example **requires Memgraph Enterprise**.
