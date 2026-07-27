# Memory Tracking and License Usage Monitoring

This example shows how to monitor Memgraph's memory usage relative to the license limit using `SHOW STORAGE INFO`.

## Background

Memgraph Enterprise licenses enforce a memory limit based on **`memory_tracked`** — the total RAM allocated and tracked by Memgraph across all databases. When `memory_tracked` reaches the `allocation_limit`, write queries are blocked (reads and deletes still work).

Key fields from `SHOW STORAGE INFO`:

| Field | Scope | Description |
|-------|-------|-------------|
| `memory_tracked` | Instance-wide | RAM allocated and tracked by Memgraph. **This is the license-enforced value.** |
| `allocation_limit` | Instance-wide | The effective memory cap — the lower of the license limit and `--memory-limit` config flag. |
| `memory_res` | Instance-wide | OS-reported resident set size. Useful for infrastructure monitoring but **not** the license-enforced value. |
| `graph_memory_tracked` | Instance-wide | Portion of `memory_tracked` used by graph structures (vertices, edges, properties). |
| `vector_index_memory_tracked` | Instance-wide | Portion of `memory_tracked` used by vector index embeddings. |
| `disk_usage` | Per-database | Disk space used by the current database. |

> **Note:** The HTTP metrics endpoint (port 9091) exposes `memory_usage` which corresponds to `memory_res` (OS-reported), not `memory_tracked`. To monitor the license-enforced value, use `SHOW STORAGE INFO` as shown below.

## Prerequisites

- Python 3.8+
- A running Memgraph instance
- Install dependencies: `pip install -r requirements.txt`

## Usage

```bash
# Basic usage — polls every 30 seconds, warns at 80% of allocation_limit
python monitor_memory.py

# Custom interval and threshold
python monitor_memory.py --host 127.0.0.1 --port 7687 --interval 10 --warn-threshold 0.75

# Single check (no polling)
python monitor_memory.py --once
```

## Example output

```
[2025-01-15 14:30:00] Memory: 12.45 GiB / 75.00 GiB (16.6%) | Graph: 11.02 GiB | Vector: 1.43 GiB | Res: 14.21 GiB
[2025-01-15 14:30:30] Memory: 12.45 GiB / 75.00 GiB (16.6%) | Graph: 11.02 GiB | Vector: 1.43 GiB | Res: 14.21 GiB
[2025-01-15 14:31:00] WARNING: Memory at 81.2% of limit! 60.90 GiB / 75.00 GiB
```

## Estimating memory before import

Before importing data, estimate your memory needs using:
- The [Storage Memory Calculator](https://memgraph.com/storage-calculator)
- The formula: `StorageRAMUsage = NumVertices x 204B + NumEdges x 154B`
- A general rule of thumb: provision **2x** the estimated dataset size to account for query execution overhead

See the [memory estimation docs](https://memgraph.com/docs/data-modeling/best-practices#final-thoughts) for more details.

## Related documentation

- [SHOW STORAGE INFO fields](https://memgraph.com/docs/database-management/server-stats#storage-information)
- [Memory control](https://memgraph.com/docs/fundamentals/storage-memory-usage#control-memory-usage)
- [Enterprise licensing](https://memgraph.com/docs/database-management/enabling-memgraph-enterprise)
- [Monitoring via HTTP server](https://memgraph.com/docs/database-management/monitoring#metrics-tracking-via-http-server-enterprise-edition)
