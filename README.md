<h1 align="center"> Memgraph Best Practices </h1>

<p align="center">
  <a href="https://memgr.ph/join-discord">
    <img src="https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"/>
  </a>
  <a href="https://memgraph.com/docs/" alt="Documentation">
    <img src="https://img.shields.io/badge/Docs-fb6d00?style=for-the-badge" alt="Documentation"/>
  </a>
</p>

<p align="center">
This repository holds examples to ease the use of Memgraph. It will be covering various topics important for any Memgraph user.
</p>

## Content

### 🟢 [Graph Modeling Best Practices](https://memgraph.com/docs/fundamentals/graph-modeling)

Learn the tips & tricks on how to best model your data and what to look after before you decide to import it.

### :card_index_dividers: [Import Best Practices](./import/)

After [installing Memgraph](https://memgraph.com/docs/getting-started), the first step is [data import](https://memgraph.com/docs/data-migration). Whether you're migrating from another database or creating a new dataset, tips & tricks from the [Import Best Practices](https://memgraph.com/docs/data-migration/best-practices) will speed up your import process, especially on a larger scale. 

If you're migrating from other databases, check the [examples](./import/migrate/) that use the `migrate` module.

### :question: [Querying Best Practices](https://memgraph.com/docs/querying/best-practices)

Querying Memgraph via Cypher is a common operation that needs to be properly optimized. [Querying Best Practices](https://memgraph.com/docs/querying/best-practices) will show how to query Memgraph and write Cypher so the queries are executed as fast as possible with the least amount of resources.

### 🚀 [Deployment Best Practices](https://memgraph.com/docs/deployment)

Deploy Memgraph using methods that suit your environment, whether it's containerized with Docker or a native Linux installation.

## List of best practices

### Debugging
- [Generating a core dump with Memgraph in Docker Compose](./debugging/docker_compose_with_core_dump_generation/)

### GraphQL
- [Simple application with Memgraph and Neo4j GraphQL](./graphql/simple_app/)

### High availability (HA)
- [Docker deployment](./ha/docker_deployment/)
- [Docker compose deployment](./ha/docker_compose_deployment/)
- [Restoration of snapshosts on an HA cluster](./ha/k8s_restore_snapshot/)

### Import
- [Importing data from Arrow Flight](./import/migrate/arrow-flight/)
- [Importing data with DuckDB](./import/migrate/duckdb/)
- [Importing data from Amazon Aurora/MySQL](./import/migrate/amazon_aurora/)
- [Importing data from Neo4j (nodes only)](./import/migrate/neo4j/migrate_nodes/)
- [Import tool from Neo4j (complete)](./import/migrate/neo4j/complete_migration/)

### Java
- [Simple Java app with ingestion and querying](./java/querying/)

### Memgraph Lab
- [Memgraph Community with Memgraph Lab deployment in Docker compose](./memgraph_lab/community_lab_docker_compose/)
- [Memgraph Lab Enterprise Edition deployment in Docker compose](./memgraph_lab/enterprise_lab_docker_compose/)
- [Memgraph Lab Enterprise Edition with remote storage deployment in Docker compose](./memgraph_lab/enterprise_lab_with_remote_storage_docker_compose/)
- [Memgraph Lab Enterprise Edition with separate remote storage deployment in Docker compose](./memgraph_lab/enterprise_lab_with_separate_remote_storage_docker_compose/)

### NeoDash
- [Connect Memgraph with NeoDash](./neodash/)

### Python
- [GQLAlchemy basic example of creating and reading nodes](./python/querying/creating_and_reading_nodes/)

### Querying
- [Explain and profile of the query](./querying/explain_profile/)
- [Path traversals tutorial](./querying/path_traversals/)


### Time-to-live
- [Node TTL demo](./ttl/node_ttl_demo/)

### Triggers
- [Triggers write-write conflict demonstration](./triggers/trigger_write_write_conflict/)

### Use cases
- [Family tree demo](./use_cases/family_tree/)

### User management
- [Creating a read only user](./user_management/creating_read_only_user/)

## Office Hours

Talk to us about data modeling, optimizing queries, defining infrastructure requirements or migrating from your existing graph database. No nonsense or sales pitch, just tech.


![](/assets/memgraph-office-hours.svg)
<p align="center">
  <a href="https://memgraph.com/office-hours" alt="OH">
    <img src="https://img.shields.io/badge/Book a call-fb6d00?style=for-the-badge" alt="OH"/>
  </a>
</p>
