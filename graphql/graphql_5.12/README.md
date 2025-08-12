# Apollo Express GraphQL App (Memgraph)

This app runs a GraphQL server using Apollo Server (Express v3) and `@neo4j/graphql` against a Memgraph instance.

## Prerequisites
- Node.js v14+
- Running Memgraph (e.g.):

```bash
docker run -it --rm -p 7687:7687 \
  memgraph/memgraph:3.4 \
  --bolt-server-name-for-init=Neo4j/5.2.0 \
  --query-callable-mappings-path=/etc/memgraph/apoc_compatibility_mappings.json
```

## Setup
1. Copy environment template and adjust values:
```bash
cp .env.example .env
```

2. Install dependencies:
```bash
npm install
```

## Run the server
```bash
npm run dev
```
It will start by default on `http://localhost:4001/graphql`.

## Ingest and Query (optional)
This directory includes Python scripts mirroring the simple example:

- `ingest_data.py` — inserts sample nodes/relationships into Memgraph
- `query_graphql.py` — queries the GraphQL API (points to port 4001)

Install Python deps and run:
```bash
pip install -r requirements.txt
python3 ingest_data.py
python3 query_graphql.py
``` 