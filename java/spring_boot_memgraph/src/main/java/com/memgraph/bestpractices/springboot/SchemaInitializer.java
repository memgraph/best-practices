package com.memgraph.bestpractices.springboot;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.data.neo4j.core.Neo4jClient;
import org.springframework.stereotype.Component;

/**
 * Creates the label-property indexes Spring Data Neo4j's generated Cypher relies
 * on. Without them Memgraph falls back to sequential scans (you'll see
 * "Consider creating a label-property index" hints in the logs).
 *
 * Runs before {@link DataLoader} (lower {@code @Order} wins) so the indexes are
 * in place before any data is written or queried.
 */
@Component
@Order(0)
public class SchemaInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(SchemaInitializer.class);

    private final Neo4jClient neo4jClient;

    public SchemaInitializer(Neo4jClient neo4jClient) {
        this.neo4jClient = neo4jClient;
    }

    @Override
    public void run(String... args) {
        // Label indexes: CREATE INDEX ON :Label. Memgraph does NOT create these
        // out of the box, so plain `MATCH (m:Movie)` scans (findAll, count,
        // deleteAll) would otherwise sweep every node. Create them first.
        createIndex("CREATE INDEX ON :Movie");
        createIndex("CREATE INDEX ON :Person");

        // Label-property indexes: CREATE INDEX ON :Label(property).
        // These back the `@Id` lookups (title / name) used throughout the example.
        createIndex("CREATE INDEX ON :Movie(title)");
        createIndex("CREATE INDEX ON :Person(name)");
    }

    private void createIndex(String statement) {
        try {
            // Index creation must run as its own (autocommit) query, which is
            // exactly how Neo4jClient executes a bare run() call.
            neo4jClient.query(statement).run();
            log.info("Ensured index: {}", statement);
        } catch (RuntimeException e) {
            // Memgraph throws if the index already exists — safe to ignore so
            // re-runs of the app stay idempotent.
            log.info("Index already present (skipping): {}", statement);
        }
    }
}
