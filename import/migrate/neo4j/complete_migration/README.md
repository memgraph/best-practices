# 🔄 Complete Migration from Neo4j to Memgraph

This example demonstrates a **complete migration** from **Neo4j 5.26** to **Memgraph 3.2.1** using the built-in `migrate.neo4j` module. This creates a complex graph structure with multiple labels, relationships, and demonstrates the full capabilities of the migration tool with optimal performance.

## 🧠 What This Example Does

The script performs the following comprehensive actions:

### 1. **Data Creation in Neo4j**
- Creates **10 different node labels**: `Label1`, `Label2`, `Label3`, `Label4`, `Label5`, `Label6`, `Label7`, `Label8`, `Label9`, `Label10`
- Inserts **100 nodes per label** (1,000 total nodes)
- Each node has properties: `id`, `name`, `description`, `created_at`, `active`
- Creates **complete bipartite relationships** between consecutive labels:
  - Every `Label1` node → Every `Label2` node (RELATES_TO_1)
  - Every `Label2` node → Every `Label3` node (RELATES_TO_2)
  - Every `Label3` node → Every `Label4` node (RELATES_TO_3)
  - Every `Label4` node → Every `Label5` node (RELATES_TO_4)
  - Every `Label5` node → Every `Label6` node (RELATES_TO_5)
  - Every `Label6` node → Every `Label7` node (RELATES_TO_6)
  - Every `Label7` node → Every `Label8` node (RELATES_TO_7)
  - Every `Label8` node → Every `Label9` node (RELATES_TO_8)
  - Every `Label9` node → Every `Label10` node (RELATES_TO_9)
- **Total relationships**: 90,000 (9 pairs × 10,000 relationships per pair)

### 2. **Schema Discovery**
- Uses `CALL apoc.meta.schema()` to discover all labels and relationship types
- Extracts node and relationship counts directly from schema metadata
- Provides detailed schema information before migration

### 3. **Optimized Migration to Memgraph**
- Uses `CALL migrate.neo4j()` for each label to migrate nodes
- Uses `CALL migrate.neo4j()` for each relationship type to migrate relationships
- Creates `__MigrationNode__(__elementId__)` index for optimal node matching
- Uses Neo4j's `elementId()` for efficient relationship creation
- Creates appropriate indexes for performance
- Verifies migration results by counting nodes and relationships

## 🚀 How to Run with Docker Compose

### Prerequisites
- Docker and Docker Compose installed
- Python 3.7+ with pip

### Step 1: Start the Services
```bash
docker-compose up -d
```

This will start:
- **Neo4j 5.26** on `localhost:7474` (browser) and `localhost:7687` (bolt)
- **Memgraph 3.2.1** on `localhost:7688` (bolt) and `localhost:3000` (Memgraph Lab)

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run the Migration
```bash
python complete_migration.py
```

## 📊 Expected Output

The script will output detailed information about:

```
=== Complete Migration from Neo4j to Memgraph ===

1. Setting up Neo4j data...
Clearing existing data in Neo4j...
Creating complete dataset in Neo4j...
Creating 100 Label1 nodes...
Creating 100 Label2 nodes...
...
Creating chained relationships...
Created RELATES_TO_1 relationships between all Label1 nodes and all Label2 nodes
Created RELATES_TO_2 relationships between all Label2 nodes and all Label3 nodes
...

2. Inspecting Neo4j schema...
Neo4j Schema Information:
Labels: ['Label1', 'Label2', 'Label3', 'Label4', 'Label5', 'Label6', 'Label7', 'Label8', 'Label9', 'Label10']
Relationship Types: ['RELATES_TO_1', 'RELATES_TO_2', 'RELATES_TO_3', 'RELATES_TO_4', 'RELATES_TO_5', 'RELATES_TO_6', 'RELATES_TO_7', 'RELATES_TO_8', 'RELATES_TO_9']
Node counts per label:
  Label1: 100
  Label2: 100
  ...
Relationship counts per type:
  RELATES_TO_1: 10000
  RELATES_TO_2: 10000
  ...

3. Starting migration to Memgraph...
[Worker 1] Connecting to Memgraph...
[Worker 1] Setting storage mode and clearing graph...
[Worker 1] Creating __MigrationNode__ index on __elementId__...
[Worker 1] Verifying Neo4j connectivity...
[Worker 1] Discovering Neo4j schema using apoc.meta.schema()...
[Worker 1] Discovered node label: Label1 (count: 100)
[Worker 1] Discovered node label: Label2 (count: 100)
...
[Worker 1] Discovered relationship type: RELATES_TO_1 (count: 10000)
[Worker 1] Discovered relationship type: RELATES_TO_2 (count: 10000)
...
[Worker 1] Starting migration of nodes...
[Worker 1] Migrating Label1 nodes...
[Worker 1] Completed migration of Label1 nodes...
...
[Worker 1] Starting migration of relationships...
[Worker 1] Migrating RELATES_TO_1 relationships...
[Worker 1] Completed migration of RELATES_TO_1 relationships...
...
[Worker 1] Verifying migration results...
[Worker 1] Label1 nodes in Memgraph: 100
[Worker 1] Label2 nodes in Memgraph: 100
...
[Worker 1] RELATES_TO_1 relationships in Memgraph: 10000
[Worker 1] RELATES_TO_2 relationships in Memgraph: 10000
...

=== Migration Complete ===
```

## 🔧 Key Features

### **Optimized Node Matching**
The migration uses Neo4j's `elementId()` for optimal performance:
- Creates `__MigrationNode__(__elementId__)` index for fast lookups
- Uses `elementId` as the primary key for node matching
- Eliminates the need for property-based node matching during relationship creation

### **Complete Bipartite Graph Structure**
Creates a dense, interconnected graph:
- Every node from one label connects to every node in the next label
- Creates 10,000 relationships per label pair
- Total of 90,000 relationships across the entire graph

### **Schema Discovery**
The script automatically discovers the Neo4j schema:
- Uses `CALL apoc.meta.schema()` to get comprehensive schema information
- Extracts labels, relationship types, and counts from schema metadata
- No hardcoded assumptions about data structure

### **Performance Optimization**
- Uses batch processing for node creation
- Creates indexes before migration
- Uses `IN_MEMORY_ANALYTICAL` storage mode for better performance
- Indexed node matching for relationship creation

## 🧾 Data Structure

### Node Properties
Each node has the following structure:
```json
{
  "id": "label1_0",
  "name": "Label1 0", 
  "description": "Random description string...",
  "created_at": "2024-01-15",
  "active": true,
  "__elementId__": "neo4j_element_id"
}
```

### Relationship Properties
Each relationship has:
```json
{
  "strength": 7
}
```

## 🔍 Verification Queries

After migration, you can verify the data in Memgraph:

```cypher
// Count all nodes by label
MATCH (n) RETURN labels(n) as labels, count(n) as count ORDER BY count DESC;

// Count all relationships by type  
MATCH ()-[r]->() RETURN type(r) as type, count(r) as count ORDER BY count DESC;

// Check the bipartite structure
MATCH (a:Label1)-[:RELATES_TO_1]->(b:Label2) 
RETURN count(a) as source_nodes, count(b) as target_nodes, count(*) as relationships;
```

## 🔖 Version Compatibility

This example was tested with:
- **Neo4j 5.26 (Enterprise, no auth)**
- **Memgraph 3.2.1 (Community)**
- **GQLAlchemy v1.7.0**
- **Python 3.8+**

## 🎯 Use Cases

This complete migration example is useful for:
- **Production migrations** from Neo4j to Memgraph
- **Testing migration tools** with complex graph structures
- **Benchmarking** migration performance with large datasets
- **Learning** how to handle multiple labels and relationships efficiently
- **Validating** data integrity during migration

## 💬 Need Help?

If you encounter issues, visit the [Memgraph Discord server](https://discord.gg/memgraph) to get help from the community or the Memgraph team!
