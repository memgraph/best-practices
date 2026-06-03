package com.memgraph.bestpractices.springboot.entities;

import static org.springframework.data.neo4j.core.schema.Relationship.Direction.INCOMING;

import java.util.HashSet;
import java.util.Set;

import org.springframework.data.neo4j.core.schema.Id;
import org.springframework.data.neo4j.core.schema.Node;
import org.springframework.data.neo4j.core.schema.Property;
import org.springframework.data.neo4j.core.schema.Relationship;

/**
 * A :Movie node together with its relationships to {@link PersonEntity}.
 *
 * Mirrors the classic Neo4j "movies" model so this example reads as a direct
 * drop-in replacement of the Spring Data Neo4j getting-started guide, but every
 * read/write below runs against Memgraph.
 */
@Node("Movie")
public class MovieEntity {

    @Id
    private final String title;

    @Property("tagline")
    private String description;

    // (:Person)-[:ACTED_IN]->(:Movie) — incoming from the movie's perspective.
    @Relationship(type = "ACTED_IN", direction = INCOMING)
    private Set<PersonEntity> actors = new HashSet<>();

    // (:Person)-[:DIRECTED]->(:Movie) — incoming from the movie's perspective.
    @Relationship(type = "DIRECTED", direction = INCOMING)
    private Set<PersonEntity> directors = new HashSet<>();

    public MovieEntity(String title, String description) {
        this.title = title;
        this.description = description;
    }

    public String getTitle() {
        return title;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public Set<PersonEntity> getActors() {
        return actors;
    }

    public void setActors(Set<PersonEntity> actors) {
        this.actors = actors;
    }

    public Set<PersonEntity> getDirectors() {
        return directors;
    }

    public void setDirectors(Set<PersonEntity> directors) {
        this.directors = directors;
    }
}
