package com.memgraph.bestpractices.springboot;

import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import com.memgraph.bestpractices.springboot.entities.MovieEntity;
import com.memgraph.bestpractices.springboot.entities.PersonEntity;
import com.memgraph.bestpractices.springboot.repositories.MovieRepository;

/**
 * Seeds Memgraph with a tiny movie graph on startup and runs a couple of
 * queries so you can see Spring Data Neo4j writing to and reading from Memgraph
 * without touching the REST API. Disable it by removing the {@code @Component}
 * annotation if you only want the HTTP endpoints.
 */
@Component
@Order(1) // runs after SchemaInitializer (@Order(0)) so indexes exist first
public class DataLoader implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataLoader.class);

    private final MovieRepository movieRepository;

    public DataLoader(MovieRepository movieRepository) {
        this.movieRepository = movieRepository;
    }

    @Override
    public void run(String... args) {
        // Start from a clean slate so re-runs are idempotent.
        movieRepository.deleteAll();

        // --- Load data ------------------------------------------------------
        PersonEntity keanu = new PersonEntity("Keanu Reeves", 1964);
        PersonEntity carrie = new PersonEntity("Carrie-Anne Moss", 1967);
        PersonEntity lana = new PersonEntity("Lana Wachowski", 1965);

        MovieEntity matrix = new MovieEntity("The Matrix", "Welcome to the Real World");
        matrix.setActors(Set.of(keanu, carrie));
        matrix.setDirectors(Set.of(lana));

        // Saving the movie persists the connected people and relationships too.
        movieRepository.save(matrix);
        log.info("Loaded {} movie(s) into Memgraph", movieRepository.count());

        // --- Query data -----------------------------------------------------
        movieRepository.findOneByTitle("The Matrix").ifPresent(m ->
                log.info("Found movie '{}' with {} actor(s) and tagline \"{}\"",
                        m.getTitle(), m.getActors().size(), m.getDescription()));

        movieRepository.findMoviesByActor("Keanu Reeves").forEach(m ->
                log.info("Keanu Reeves acted in: {}", m.getTitle()));
    }
}
