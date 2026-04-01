# PySpark <-> Memgraph Integration

Ingest CSV data into Memgraph through PySpark using the Neo4j Spark Connector.

## Architecture

```
CSV files ──> PySpark (local) ──> Memgraph (via Neo4j Spark Connector)
```

## Prerequisites

- Java 11+
- Python 3.8+ (3.12 recommended)
- Docker (for Memgraph)

## Quick Start (Spark 3.5 — recommended)

```bash
# 1. Start Memgraph
docker compose up -d

# 2. Create a venv and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install --timeout 300 -r requirements.txt

# 3. Generate sample CSV data (10k nodes, 50k edges)
python generate_data.py

# 4. Ingest into Memgraph via PySpark
python csv_to_memgraph.py

# 5. (optional) Custom CSV paths
python csv_to_memgraph.py /path/to/nodes.csv /path/to/edges.csv
```

## Running with Spark 3.3

```bash
cd spark33
python -m venv .venv
source .venv/bin/activate
pip install --timeout 300 -r requirements.txt

# Generate data (shared script in parent dir)
python ../generate_data.py

# Run (reads nodes.csv and edges.csv from current dir)
cp ../nodes.csv ../edges.csv .
python csv_to_memgraph.py
```

## Running with Spark 3.4

```bash
cd spark34
python -m venv .venv
source .venv/bin/activate
pip install --timeout 300 -r requirements.txt

python ../generate_data.py
cp ../nodes.csv ../edges.csv .
python csv_to_memgraph.py
```

## Version Matrix

| Directory  | PySpark | Neo4j Spark Connector   |
|------------|---------|-------------------------|
| `/` (root) | 3.5.x   | 5.4.0_for_spark_3       |
| `spark34/` | 3.4.x   | 5.4.0_for_spark_3       |
| `spark33/` | 3.3.x   | 5.1.0_for_spark_3       |

The Neo4j Spark Connector JAR is downloaded automatically by Spark on first run
via `spark.jars.packages` — no manual JAR installation needed.

**Note:** PySpark 4.x is not supported — the Neo4j Spark Connector only supports Spark 3.x.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEMGRAPH_URI` | `bolt://localhost:7687` | Memgraph Bolt endpoint |

## CSV Format

**nodes.csv**
```
id,label,name,age_or_value
1,Person,Alice_1,34
2,Company,Acme_2,500000
3,Product,Widget_3,49.99
```

**edges.csv**
```
source,target,weight
1,2,3.45
2,3,7.12
```

## Files

```
pyspark_integration/
├── docker-compose.yml         # Memgraph MAGE 3.9.0
├── generate_data.py           # Create sample nodes.csv & edges.csv
├── csv_to_memgraph.py         # PySpark 3.5 -> Memgraph
├── requirements.txt           # PySpark 3.5 deps
├── spark33/
│   ├── csv_to_memgraph.py     # PySpark 3.3 -> Memgraph
│   └── requirements.txt
└── spark34/
    ├── csv_to_memgraph.py     # PySpark 3.4 -> Memgraph
    └── requirements.txt
```
