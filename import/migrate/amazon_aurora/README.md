# Amazon Aurora to Memgraph Migration

This directory contains a complete example of migrating data from Amazon Aurora (MySQL-compatible) to Memgraph using the `migrate.mysql()` procedure from MAGE.

## Overview

The migration process involves:
1. Setting up Amazon Aurora (MySQL) and Memgraph using Docker Compose
2. Creating and populating tables in Aurora with sample data
3. Migrating the data to Memgraph using the `migrate.mysql()` procedure
4. Verifying the migration results

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ with pip
- Network access to download Docker images

## Setup

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the services:**
   ```bash
   docker-compose up -d
   ```

   This will start:
   - Amazon Aurora (MySQL 8.0) on port 3306
   - Memgraph with MAGE on port 7688 (Bolt) and 3000 (HTTP)

3. **Wait for services to be ready:**
   ```bash
   # Check if Aurora is ready
   docker-compose logs aurora
   
   # Check if Memgraph is ready
   docker-compose logs memgraph
   ```

## Usage

### Running the Complete Migration

The main script `migrate.py` performs the entire migration process:

```bash
python migrate.py
```

This script will:
1. **Clear existing data** in Aurora (drop all tables)
2. **Create sample tables** with relationships
3. **Populate tables** with random data
4. **Migrate data** to Memgraph using `migrate.mysql()`
5. **Verify migration** results

### What the Script Creates

The script creates a sample dataset with:

- **5 main tables** (Table1, Table2, ..., Table5) with 100 rows each
- **4 relationship tables** (RelTable1, RelTable2, ..., RelTable4) connecting consecutive tables
- **Rich data structure** including:
  - Primary keys and foreign keys
  - Various data types (VARCHAR, TEXT, DATE, BOOLEAN, INT, DECIMAL, JSON)
  - Random relationships between all rows of consecutive tables

### Migration Process

The migration uses the `migrate.mysql()` procedure which:

1. **Switches Memgraph to analytical mode** (`STORAGE MODE IN_MEMORY_ANALYTICAL`)
2. **Drops the existing graph** (`DROP GRAPH`)
3. **Creates necessary indices** for migration
4. **Discovers the database schema** automatically
5. **Migrates all tables** as nodes with their properties
6. **Migrates relationships** based on foreign key constraints
7. **Creates a snapshot** for persistence

## Configuration

### Aurora Configuration

The Aurora MySQL instance is configured with:
- **Host:** localhost (or `aurora` from within Docker network)
- **Port:** 3306
- **Database:** testdb
- **User:** testuser
- **Password:** testpass

### Memgraph Configuration

Memgraph is configured with:
- **Host:** localhost (or `memgraph` from within Docker network)
- **Port:** 7688 (Bolt protocol)
- **MAGE extensions:** Enabled for migration procedures

## Verification

After migration, you can verify the results:

### Check Aurora Data
```bash
# Connect to Aurora
mysql -h localhost -P 3306 -u testuser -ptestpass testdb

# List tables
SHOW TABLES;

# Check data
SELECT COUNT(*) FROM Table1;
```

### Check Memgraph Data
```bash
# Connect to Memgraph (using mgconsole or any Cypher client)
# Or use the HTTP API at http://localhost:3000

# Check node labels
SHOW DATABASE INFO YIELD node_labels;

# Check relationship types
SHOW DATABASE INFO YIELD relationship_types;

# Count nodes and relationships
MATCH (n) RETURN count(n) as node_count;
MATCH ()-[r]->() RETURN count(r) as relationship_count;
```

## Troubleshooting

### Common Issues

1. **Connection refused errors:**
   - Ensure Docker Compose services are running
   - Check if ports are available (3306, 7688, 3000)
   - Wait for services to fully start

2. **Migration timeout:**
   - The script includes a 5-second wait for services
   - Increase the wait time if needed
   - Check service logs for errors

3. **Authentication errors:**
   - Verify the Aurora credentials in the script
   - Ensure the database `testdb` exists

4. **Memory issues:**
   - The script creates 500 nodes and 40,000 relationships
   - Ensure sufficient memory for both Aurora and Memgraph

### Debugging

Enable debug logging:
```bash
# Check Aurora logs
docker-compose logs aurora

# Check Memgraph logs
docker-compose logs memgraph

# Run with verbose output
python complete_migration.py
```

## Customization

### Modifying the Dataset

You can customize the dataset by modifying these variables in `migrate.py`:

```python
TABLES = [f"Table{i}" for i in range(1, 6)]  # Number of tables
ROWS_PER_TABLE = 100  # Rows per table
RELATIONSHIP_TABLES = [f"RelTable{i}" for i in range(1, 5)]  # Relationship tables
```

### Adding Custom Tables

To add custom tables, modify the `ensure_aurora_has_data()` function:

```python
# Add your custom table creation logic
create_custom_table_query = """
CREATE TABLE custom_table (
    id VARCHAR(50) PRIMARY KEY,
    custom_field VARCHAR(100)
)
"""
cursor.execute(create_custom_table_query)
```

## Cleanup

To stop and clean up the services:

```bash
# Stop services
docker-compose down

# Remove volumes (this will delete all data)
docker-compose down -v
```

## Notes

- This example uses MySQL 8.0 as a stand-in for Amazon Aurora MySQL
- For production Aurora, update the connection parameters to point to your Aurora cluster
- The migration preserves data types and relationships
- JSON fields are preserved as properties in Memgraph
- Foreign key relationships are converted to graph relationships 