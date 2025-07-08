# NeoDash with Memgraph Docker Compose Setup

This Docker Compose configuration sets up NeoDash (a graph visualization tool) with Memgraph database for easy graph exploration and visualization.

## Services

### Memgraph
- **Image**: `memgraph/memgraph-mage:3.3`
- **Ports**: 
  - `7687` - Bolt protocol (for NeoDash connection)
  - `7444` - HTTP API
  - `9091` - Metrics endpoint
- **Features**: Includes MAGE (Memgraph Advanced Graph Extensions) for additional algorithms

### NeoDash
- **Image**: `neodash/neodash:latest`
- **Port**: `5000` - Web interface
- **Features**: Graph visualization and exploration tool

## Quick Start

1. **Start the services**:
   ```bash
   docker-compose up -d
   ```

2. **Access NeoDash**:
   - Open your browser and go to `http://localhost:5005`
   - NeoDash will automatically connect to Memgraph

3. **Connect to Memgraph directly** (optional):
   - Use any Cypher client to connect to `bolt://localhost:7687`

## Configuration

### Environment Variables

You can customize the setup by modifying the environment variables in `docker-compose.yml`:

- `NEO4J_URI`: Connection string for Memgraph
- `NEO4J_USER`: Username (default: neo4j)
- `NEO4J_PASSWORD`: Password (default: password)
- `NEO4J_DATABASE`: Database name (default: neo4j)

### Ports

- **NeoDash**: `http://localhost:5005`
- **Memgraph Bolt**: `bolt://localhost:7687`
- **Memgraph HTTP API**: `http://localhost:7444`
- **Memgraph Metrics**: `http://localhost:9091`

## Data Persistence

The Memgraph data is persisted in a Docker volume named `memgraph_data`. This ensures your data survives container restarts.

## Stopping the Services

```bash
# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes (WARNING: This will delete all data)
docker-compose down -v
```
