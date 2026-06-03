package com.memgraph.bestpractices.springboot.repositories;

import java.util.Optional;

import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;

import com.memgraph.bestpractices.springboot.entities.MovieEntity;

/**
 * Spring Data repository for {@link MovieEntity}.
 *
 * Extending {@link Neo4jRepository} gives you CRUD (save, findAll, findById,
 * deleteById, ...) for free. Spring derives the Cypher for the derived query
 * method below from its name, and you can drop down to explicit Cypher with
 * {@code @Query} when you want full control — both run unmodified on Memgraph.
 */
public interface MovieRepository extends Neo4jRepository<MovieEntity, String> {

    // Derived query: Spring generates `MATCH (m:Movie) WHERE m.title = $title ...`
    Optional<MovieEntity> findOneByTitle(String title);

    // Explicit Cypher: find the movies a given actor played in.
    // Standard Cypher, executed as-is by Memgraph.
    @Query("MATCH (p:Person {name: $name})-[:ACTED_IN]->(m:Movie) RETURN m")
    Iterable<MovieEntity> findMoviesByActor(@Param("name") String name);
}
