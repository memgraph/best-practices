# Tableau with Memgraph

This guide shows how to connect Tableau to Memgraph for graph analytics and visualization through Tableau dashboards.

## Prerequisites

- Docker and Docker Compose installed
- Tableau Desktop or Tableau Server installed
- [Neo4j JDBC driver](https://github.com/neo4j-contrib/neo4j-jdbc) (compatible with Memgraph's Bolt protocol)

## Setup

### 1. Start Memgraph

```bash
docker compose up -d
```

This starts Memgraph MAGE with the following ports:

| Port   | Description      |
|--------|------------------|
| `7687` | Bolt protocol    |
| `7444` | HTTP API         |
| `9091` | Metrics endpoint |

### 2. Install the JDBC Driver

Download the [Neo4j JDBC driver JAR](https://github.com/neo4j-contrib/neo4j-jdbc) and place it in Tableau's driver directory:

- **Windows**: `C:\Program Files\Tableau\Drivers`
- **macOS**: `~/Library/Tableau/Drivers`
- **Linux**: `/opt/tableau/tableau_driver/jdbc`

### 3. Connect Tableau to Memgraph

In Tableau Desktop (or Tableau Server web authoring):

1. Go to **Connect** → **Other Databases (JDBC)**.
2. Enter the JDBC URL:

   ```
   jdbc:neo4j:bolt://localhost:7687
   ```

3. Leave the username and password fields empty (unless authentication is configured on Memgraph).
4. Click **Sign In**.

## Tableau Server in a Container

Tableau does not provide a public Docker image for Tableau Server. If you want to run Tableau Server in Docker, you need to build the image yourself using the [Tableau Server in a Container Setup Tool](https://help.tableau.com/current/server-linux/en-us/server-in-container_image.htm).

Once built, you can add it to the `docker-compose.yml` and use `memgraph:7687` as the Bolt endpoint (both services share the `memgraph-network`).

## Data Persistence

Memgraph data is persisted in the `memgraph_data` Docker volume, ensuring data survives container restarts.

## Stopping the Services

```bash
# Stop and remove containers
docker compose down

# Stop and remove containers + volumes (WARNING: deletes all data)
docker compose down -v
```
