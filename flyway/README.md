# Schema Migrations with Flyway and Memgraph

Manage versioned graph schema migrations against Memgraph using [Flyway](https://flywaydb.org/) with the [Neo4j JDBC driver](https://github.com/neo4j/neo4j-jdbc) and [neo4j-flyway-database](https://github.com/michael-simons/neo4j-flyway-database) plugin. Memgraph's Bolt protocol compatibility allows the Neo4j JDBC driver to connect directly.

## Architecture

```
sql/
  ├── V1__Create_indexes.cypher       Versioned .cypher
  ├── V2__Seed_graph.cypher           migrations executed
  └── V3__Schema_evolution.cypher     via Bolt protocol
         │
         ▼
  ┌──────────────┐    Bolt (7687)    ┌─────────────┐
  │    Flyway     │ ────────────────> │  Memgraph   │
  │  (Neo4j JDBC) │                   │  (MAGE)     │
  └──────────────┘                   └─────────────┘
```

## What This Example Does

1. **Creates indexes** on `Person(email)`, `Person(name)`, and `Company(name)` for fast lookups.
2. **Seeds the graph** with Person and Company nodes connected by `WORKS_AT` relationships.
3. **Evolves the schema** by adding `KNOWS` relationships, enriching `WORKS_AT` with a `department` property, and adding an `active` flag to all Person nodes.
4. **Tracks every migration** using Flyway's history graph (`__Neo4jMigration` nodes linked by `MIGRATED_TO` relationships).
5. **Prevents re-execution** — each versioned migration runs exactly once, verified by checksum.

## How It Works

Flyway connects to Memgraph via the [Neo4j JDBC driver](https://github.com/neo4j/neo4j-jdbc) (which speaks the Bolt protocol natively). The [neo4j-flyway-database](https://github.com/michael-simons/neo4j-flyway-database) plugin implements Flyway's database SPI, enabling Flyway to:

- Recognize `jdbc:neo4j://` connection URLs
- Parse `.cypher` migration files
- Store migration history as a graph (not a SQL table)

Migration history is stored as `__Neo4jMigration` nodes linked by `MIGRATED_TO` relationships. This is the same format used by the standalone [neo4j-migrations](https://github.com/michael-simons/neo4j-migrations) tool.

The `--bolt-server-name-for-init=Neo4j/5.2.0` flag on Memgraph ensures the Neo4j JDBC driver recognizes it as a compatible Bolt endpoint.

## Quick Start

```bash
# 1. Start Memgraph and run all migrations
docker compose up --build

# 2. (optional) Verify the migration results
pip install -r requirements.txt
python verify_migration.py
```

The `flyway` container applies all migrations and exits. Memgraph stays running on `bolt://localhost:7687` and the Lab UI is available at `http://localhost:3000`.

## Running Additional Flyway Commands

After the initial `docker compose up`, you can run more Flyway commands against the running Memgraph instance:

```bash
# Check migration status
docker compose run --rm flyway info

# Validate applied migrations (checksum verification)
docker compose run --rm flyway validate

# Repair the migration history (fix checksums or remove failed entries)
docker compose run --rm flyway repair
```

## Project Structure

```
flyway/
├── README.md                              # This file
├── docker-compose.yml                     # Memgraph + Flyway services
├── Dockerfile.flyway                      # Flyway image with Neo4j JDBC + plugin
├── flyway.conf                            # Flyway configuration
├── sql/
│   ├── V1__Create_indexes.cypher          # Migration 1: index creation
│   ├── V2__Seed_graph.cypher              # Migration 2: initial nodes and relationships
│   └── V3__Schema_evolution.cypher        # Migration 3: new rels, properties
├── requirements.txt                       # Python deps for verification script
└── verify_migration.py                    # Verify migration results
```

## Migration File Naming

Flyway uses a strict naming convention:

| Pattern | Description |
|---------|-------------|
| `V1__Description.cypher` | Versioned migration (runs once, in order) |
| `V1.1__Description.cypher` | Sub-versioned migration |
| `R__Description.cypher` | Repeatable migration (runs on every change) |
| `U1__Description.cypher` | Undo migration (Flyway Teams only) |

The double underscore `__` separates the version from the description. Descriptions use underscores instead of spaces.

## Writing Memgraph-Compatible Migrations

When writing Cypher for Memgraph migrations, keep these syntax differences in mind compared to Neo4j:

| Operation | Memgraph | Neo4j |
|-----------|----------|-------|
| Create index | `CREATE INDEX ON :Label(prop)` | `CREATE INDEX FOR (n:Label) ON (n.prop)` |
| Drop index | `DROP INDEX ON :Label(prop)` | `DROP INDEX name` |
| Unique constraint | `CREATE CONSTRAINT ON (n:Label) ASSERT n.prop IS UNIQUE` | `CREATE CONSTRAINT FOR (n:Label) REQUIRE n.prop IS UNIQUE` |
| Existence constraint | `CREATE CONSTRAINT ON (n:Label) ASSERT EXISTS (n.prop)` | `CREATE CONSTRAINT FOR (n:Label) REQUIRE n.prop IS NOT NULL` |

Stick to **standard Cypher** (`CREATE`, `MATCH`, `MERGE`, `SET`, `DELETE`) for maximum compatibility. Avoid Neo4j-specific features like `CALL {} IN TRANSACTIONS` or APOC procedures.

Each statement in a `.cypher` file must end with a semicolon (`;`). Flyway splits on semicolons to execute statements individually.

## Flyway vs Liquibase

Both tools can manage graph migrations against Memgraph. Key differences:

| Aspect | Flyway | Liquibase |
|--------|--------|-----------|
| Migration format | Plain `.cypher` files | XML, YAML, JSON, or Cypher changelogs |
| History storage | `__Neo4jMigration` nodes + `MIGRATED_TO` rels | `__LiquibaseChangeLog` nodes |
| Naming convention | `V{version}__description.cypher` | `id` + `author` per changeset |
| Rollback | Undo migrations (Teams only) | Rollback blocks (Community) |
| Approach | SQL-first, file-per-migration | Changelog-first, changeset-based |

See the [Liquibase example](../liquibase/) in this repository for comparison.

## Compatibility Notes

- **Memgraph v2.11+** defaults `--bolt-server-name-for-init` to a Neo4j-compatible value. The flag in `docker-compose.yml` is kept explicit for clarity.
- The `neo4j-flyway-database` plugin stores migration history as graph nodes with `__Neo4jMigration` labels and `MIGRATED_TO` relationships. These can be queried: `MATCH (m:__Neo4jMigration) RETURN m ORDER BY m.version`.
- The plugin uses some Neo4j-specific Cypher internally (e.g., `CREATE CONSTRAINT ... IF NOT EXISTS`). If Memgraph does not support certain syntax, check the [neo4j-flyway-database GitHub](https://github.com/michael-simons/neo4j-flyway-database) for updates.
- The Neo4j JDBC driver (v6.x) speaks Bolt natively — it is **not** built on top of the Neo4j Java Driver.

## Version Compatibility

This example was tested with:

* **Memgraph MAGE 3.9.0**
* **Flyway 11.1.0**
* **Neo4j JDBC Full Bundle 6.12.1**
* **neo4j-flyway-database 0.0.4**

## Need Help?

If you encounter issues, visit the [Memgraph Discord server](https://discord.gg/memgraph) to get help from the community or the Memgraph team!
