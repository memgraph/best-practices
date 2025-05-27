# 💾 Run Memgraph with Manual Snapshotting Using Docker Compose

This setup launches **Memgraph 3.2.1 with MAGE** in a Docker container, with **manual-only snapshotting enabled**. It disables all periodic snapshots and WAL (Write-Ahead Logging), giving you complete control over when snapshots are taken.

## 📦 What This Setup Does

* **Starts a Memgraph instance** with:

  * **No automatic snapshots**
  * **Write-Ahead Logging disabled**
  * **Verbose logging enabled**
* **Mounts persistent volumes** for:

  * Data (`/var/lib/memgraph`)
  * Logs (`/var/log/memgraph`)

## 🚀 How to Start Memgraph

Launch the container in the background:

```bash
docker-compose up -d
```

Check logs in real time:

```bash
docker logs -f memgraph
```

## 💾 Manual Snapshot Instructions

To take a **manual snapshot** from within Memgraph, open a `mgconsole` or connect via Bolt (e.g. with `gqlalchemy`) and run:

```cypher
CREATE SNAPSHOT;
```

> This command writes the current in-memory data to disk under `/var/lib/memgraph`.

## 🔍 Connect to Memgraph

You can connect to Memgraph using:

* **Bolt protocol** on port `7687`
* **Memgraph Lab** or any Bolt-compatible client
* **mgconsole** (install locally or run interactively inside the container)

Example:

```bash
docker exec -it memgraph mgconsole
```

## 🔒 Data Persistence

Mounted volumes ensure that both data and logs persist even if the container restarts:

* `memgraph_data`: stores snapshots and in-memory data
* `memgraph_logs`: stores detailed logs (TRACE level)

## 🧾 Version Info

* **Memgraph**: 3.2.1 Community Edition (with MAGE)
* **Snapshot Mode**: Manual-only
* **WAL**: Disabled

## 💬 Need Help?

Join the [Memgraph Discord server](https://discord.gg/memgraph) for questions, tips, or troubleshooting.

