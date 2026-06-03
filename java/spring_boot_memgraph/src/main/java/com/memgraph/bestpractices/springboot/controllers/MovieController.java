package com.memgraph.bestpractices.springboot.controllers;

import com.memgraph.bestpractices.springboot.entities.MovieEntity;
import com.memgraph.bestpractices.springboot.repositories.MovieRepository;

import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Minimal REST API so you can load and query data over HTTP.
 *
 * Every endpoint delegates straight to the {@link MovieRepository}, i.e. to
 * Spring Data Neo4j running against Memgraph.
 */
@RestController
@RequestMapping("/movies")
public class MovieController {

    private final MovieRepository movieRepository;

    public MovieController(MovieRepository movieRepository) {
        this.movieRepository = movieRepository;
    }

    // PUT /movies — create or update a movie (MERGE/SET under the hood).
    @PutMapping
    MovieEntity createOrUpdateMovie(@RequestBody MovieEntity movie) {
        return movieRepository.save(movie);
    }

    // GET /movies — list all movies.
    @GetMapping({"", "/"})
    Iterable<MovieEntity> getMovies() {
        return movieRepository.findAll();
    }

    // GET /movies/by-title?title=The%20Matrix — fetch one movie by title.
    @GetMapping("/by-title")
    MovieEntity byTitle(@RequestParam String title) {
        return movieRepository.findOneByTitle(title).orElse(null);
    }

    // GET /movies/by-actor?name=Keanu%20Reeves — movies a person acted in.
    @GetMapping("/by-actor")
    Iterable<MovieEntity> byActor(@RequestParam String name) {
        return movieRepository.findMoviesByActor(name);
    }

    // DELETE /movies/{title} — remove a movie by its id (title).
    @DeleteMapping("/{title}")
    void delete(@PathVariable String title) {
        movieRepository.deleteById(title);
    }
}
