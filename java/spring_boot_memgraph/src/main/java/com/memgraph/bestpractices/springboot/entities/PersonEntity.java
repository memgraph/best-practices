package com.memgraph.bestpractices.springboot.entities;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;

/**
 * A :Person node.
 *
 * We use an *assigned* business key ({@code name}) as the {@code @Id} rather than
 * a generated internal id. This is the recommended approach with Memgraph: it
 * keeps the mapping portable and avoids relying on internal node ids, which are
 * not stable identifiers to build your domain on.
 */
@Node("Person")
public class PersonEntity {

    @Id
    private final String name;

    @Property("born")
    private final Integer born;

    public PersonEntity(String name, Integer born) {
        this.name = name;
        this.born = born;
    }

    public String getName() {
        return name;
    }

    public Integer getBorn() {
        return born;
    }
}
