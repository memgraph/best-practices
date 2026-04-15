# Schema Migrations with Liquibase and Memgraph

Manage versioned, trackable graph schema migrations against Memgraph using [Liquibase](https://www.liquibase.org/) and its [Neo4j extension](https://neo4j.com/labs/liquibase/docs/). Memgraph's Bolt protocol compatibility allows the Neo4j Liquibase plugin to run Cypher-based changelogs directly against Memgraph.

## Architecture

```
changelog.xml (master)
  ├── 001-create-indexes.xml      Cypher changesets
  ├── 002-seed-graph.xml          executed via Bolt
  └── 003-schema-evolution.xml    against Memgraph
         │
         ▼
  ┌─────────────┐     Bolt (7687)     ┌─────────────┐
  │  Liquibase   │ ──────────────────> │  Memgraph   │
  │  (Neo4j ext) │                     │  (MAGE)     │
  └─────────────┘                     └─────────────┘
```

## What This Example Does

1. **Creates indexes** on `Person(email)`, `Person(name)`, and `Company(name)` for fast lookups.
2. **Seeds the graph** with Person and Company nodes connected by `WORKS_AT` relationships.
3. **Evolves the schema** by adding `KNOWS` relationships, enriching `WORKS_AT` with a `department` property, and adding an `active` flag to all Person nodes.
4. **Tracks every change** in Liquibase's internal history graph so migrations are never applied twice.
5. **Supports rollback** — every changeset defines undo instructions.

## How It Works

Liquibase's Neo4j extension connects to Memgraph over the Bolt protocol. Each changeset contains standard Cypher queries. Liquibase tracks which changesets have been applied by storing a history graph (nodes prefixed with `__Liquibase`) directly inside the database. On subsequent runs, only new or modified changesets are executed.

The key configuration that makes this work is `--bolt-server-name-for-init=Neo4j/5.2.0` on the Memgraph container, which ensures the Neo4j Java driver (used internally by Liquibase) recognizes Memgraph as a compatible Bolt endpoint.

## Quick Start

```bash
# 1. Start Memgraph and run all migrations
docker compose up --build

# 2. (optional) Verify the migration results
pip install -r requirements.txt
python verify_migration.py
```

The `liquibase` container runs the migrations and exits. Memgraph stays running on `bolt://localhost:7687` and the Lab UI is available at `http://localhost:3000`.

## Running Specific Liquibase Commands

After the initial `docker compose up`, you can run additional Liquibase commands against the running Memgraph instance:

```bash
# Check migration status
docker compose run --rm liquibase \
  --defaults-file=/liquibase/liquibase.properties \
  --changelog-file=changelog.xml \
  --search-path=/liquibase/changelog \
  status

# Rollback the last changeset
docker compose run --rm liquibase \
  --defaults-file=/liquibase/liquibase.properties \
  --changelog-file=changelog.xml \
  --search-path=/liquibase/changelog \
  rollback-count 1

# Generate a SQL (Cypher) preview without applying
docker compose run --rm liquibase \
  --defaults-file=/liquibase/liquibase.properties \
  --changelog-file=changelog.xml \
  --search-path=/liquibase/changelog \
  update-sql
```

## Project Structure

```
liquibase/
├── README.md                          # This file
├── docker-compose.yml                 # Memgraph + Liquibase services
├── Dockerfile.liquibase               # Liquibase image with Neo4j extension
├── liquibase.properties               # Connection configuration
├── changelog.xml                      # Master changelog (includes all changesets)
├── changesets/
│   ├── 001-create-indexes.xml         # Index creation
│   ├── 002-seed-graph.xml             # Initial nodes and relationships
│   └── 003-schema-evolution.xml       # Schema changes (new rels, properties)
├── requirements.txt                   # Python deps for verification script
└── verify_migration.py                # Verify migration results
```

## Changelog Formats

This example uses XML changelogs, but the Neo4j extension also supports **native Cypher format**. The same migration in Cypher format would look like:

```cypher
--liquibase formatted cypher

--changeset memgraph:create-person-email-index
CREATE INDEX ON :Person(email)
--rollback DROP INDEX ON :Person(email)

--changeset memgraph:create-person-nodes
CREATE (:Person {name: 'Alice', email: 'alice@memgraph.io', role: 'Engineer'})
--rollback MATCH (p:Person {email: 'alice@memgraph.io'}) DETACH DELETE p
```

YAML and JSON formats are also supported. See the [Liquibase Neo4j docs](https://neo4j.com/labs/liquibase/docs/) for all format examples.

## Writing Memgraph-Compatible Changesets

When writing Cypher for Memgraph changesets, keep these syntax differences in mind compared to Neo4j:

| Operation | Memgraph | Neo4j |
|-----------|----------|-------|
| Create index | `CREATE INDEX ON :Label(prop)` | `CREATE INDEX FOR (n:Label) ON (n.prop)` |
| Drop index | `DROP INDEX ON :Label(prop)` | `DROP INDEX name` |
| Unique constraint | `CREATE CONSTRAINT ON (n:Label) ASSERT n.prop IS UNIQUE` | `CREATE CONSTRAINT FOR (n:Label) REQUIRE n.prop IS UNIQUE` |
| Existence constraint | `CREATE CONSTRAINT ON (n:Label) ASSERT EXISTS (n.prop)` | `CREATE CONSTRAINT FOR (n:Label) REQUIRE n.prop IS NOT NULL` |

Stick to **standard Cypher** (`CREATE`, `MATCH`, `MERGE`, `SET`, `DELETE`) for maximum compatibility. Avoid Neo4j-specific features like `CALL {} IN TRANSACTIONS` or APOC procedures.

## Compatibility Notes

- **Memgraph v2.11+** defaults `--bolt-server-name-for-init` to a Neo4j-compatible value, so the flag in `docker-compose.yml` is technically optional on recent versions but kept explicit for clarity.
- The `liquibase-neo4j` extension stores migration history as graph nodes with labels prefixed by `__Liquibase`. These are regular nodes and can be queried: `MATCH (n) WHERE any(l IN labels(n) WHERE l STARTS WITH '__Liquibase') RETURN n`.
- If you encounter issues with the Neo4j extension's internal queries, check the [liquibase-neo4j GitHub](https://github.com/liquibase/liquibase-neo4j) for the latest compatibility information.

## Version Compatibility

This example was tested with:

* **Memgraph MAGE 3.9.0**
* **Liquibase 4.29.2**
* **liquibase-neo4j 4.29.2**
* **Neo4j Java Driver 5.26.0**

## Need Help?

If you encounter issues, visit the [Memgraph Discord server](https://discord.gg/memgraph) to get help from the community or the Memgraph team!
