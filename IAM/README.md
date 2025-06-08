# PostgreSQL to Memgraph IAM Migration Example

This example demonstrates how to migrate an Identity and Access Management (IAM) system from PostgreSQL to Memgraph, showcasing efficient data migration techniques and graph-based permission analysis.

## 🧠 What This Example Does

The project consists of several components that work together:

1. **PostgreSQL Data Generation** (`postgres_iam.py`):
   - Creates synthetic IAM data in PostgreSQL
   - Generates Users (100k), Groups (30), Roles (30), Apps (300), and Permissions (10)
   - Establishes relationships between entities

2. **Index Creation** (`create_indices.py`):
   - Creates optimized indices in PostgreSQL for better JOIN performance
   - Sets up Memgraph indices for efficient graph traversal
   - Verifies index creation in both databases

3. **Data Migration** (`memgraph_migrate.py`):
   - Implements parallel processing for efficient user migration
   - Migrates all nodes and relationships to Memgraph
   - Provides detailed performance metrics
   - Achieves high throughput (170k+ users/s)

4. **Permission Analysis** (`permission_analysis.py`):
   - Analyzes user permissions and access paths
   - Performs detailed permission checks
   - Demonstrates graph-based access path discovery
   - Shows real-world IAM query scenarios

5. **Orchestration** (`run_demo.py`):
   - Coordinates all components
   - Provides comprehensive output
   - Measures performance metrics

## 🚀 How to Run Required Services

To run the required services using Docker:

```bash
# Start PostgreSQL
docker run -d --name postgres -e POSTGRES_USER=memgraph -e POSTGRES_PASSWORD=memgraph -p 5432:5432 postgres:latest

# Start Memgraph
docker run -it --rm -p 7687:7687 memgraph/memgraph:latest

# Run the demo
python3 run_demo.py
```

## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include:

```
sqlalchemy
psycopg2-binary
gqlalchemy
python-dotenv
tqdm
```

## 📦 PostgreSQL Setup

### Installation (Ubuntu)

1. Install PostgreSQL:
```bash
# Add PostgreSQL repository
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -

# Update package list and install PostgreSQL
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib
```

2. Start PostgreSQL service:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

3. Set up PostgreSQL user and database:
```bash
# Switch to postgres user
sudo -i -u postgres

# Create database
createdb iam_demo

# Create user (if not using default postgres user)
createuser --interactive
# Follow prompts to create a new user if needed

# Access PostgreSQL prompt
psql

# Set password for memgraph user
ALTER USER memgraph PASSWORD 'memgraph';

# Exit PostgreSQL prompt
\q

# Exit postgres user shell
exit
```

### Database Schema

The database will be automatically created when running `postgres_iam.py`, but here's the schema for reference:

```sql
-- Users table
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- Groups table
CREATE TABLE groups (
    name VARCHAR(255) PRIMARY KEY
);

-- Roles table
CREATE TABLE roles (
    name VARCHAR(255) PRIMARY KEY
);

-- Apps table
CREATE TABLE apps (
    name VARCHAR(255) PRIMARY KEY
);

-- Permissions table
CREATE TABLE permissions (
    name VARCHAR(255) PRIMARY KEY
);

-- User-Group relationships
CREATE TABLE user_groups (
    user_id VARCHAR(255) REFERENCES users(id),
    group_id VARCHAR(255) REFERENCES groups(name),
    PRIMARY KEY (user_id, group_id)
);

-- Group-Role relationships
CREATE TABLE group_roles (
    group_id VARCHAR(255) REFERENCES groups(name),
    role_id VARCHAR(255) REFERENCES roles(name),
    PRIMARY KEY (group_id, role_id)
);

-- Role-App relationships
CREATE TABLE role_apps (
    role_id VARCHAR(255) REFERENCES roles(name),
    app_id VARCHAR(255) REFERENCES apps(name),
    PRIMARY KEY (role_id, app_id)
);

-- App-Permission relationships
CREATE TABLE app_permissions (
    app_id VARCHAR(255) REFERENCES apps(name),
    permission_id VARCHAR(255) REFERENCES permissions(name),
    PRIMARY KEY (app_id, permission_id)
);
```

### Verify Installation

Test your PostgreSQL setup:
```bash
# Try connecting to the database
psql -h localhost -U memgraph -d iam_demo

# If successful, you should see the psql prompt
iam_demo=#

# List tables (after running postgres_iam.py)
\dt

# Exit
\q
```

## 🔧 Configuration

Create a `.env` file with:

```env
DB_USER=memgraph
DB_PASS=memgraph
DB_HOST=localhost
DB_NAME=iam_demo
MEMGRAPH_HOST=localhost
MEMGRAPH_PORT=7687
```

## 🧪 How to Run the Demo

Once PostgreSQL and Memgraph are running:

```bash
# Run the complete demo
python3 run_demo.py

# Or run individual components
python3 postgres_iam.py      # Generate PostgreSQL data
python3 create_indices.py    # Create database indices
python3 memgraph_migrate.py  # Migrate data to Memgraph
python3 permission_analysis.py  # Run permission analysis
```

## 📊 Performance Metrics

Current performance benchmarks:

- Total migration time: ~22s
- User migration rate: 170,592 nodes/s
- Relationship migration rate: 13,239 rels/s
- Total demo execution time: ~52s

## 🔖 Version Compatibility

This example was built and tested with:

- **PostgreSQL 16.0**
- **Memgraph 3.2**
- **Python 3.8+**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph).

## 🏢 Enterprise or Community?

This example works with **Memgraph Community Edition** 