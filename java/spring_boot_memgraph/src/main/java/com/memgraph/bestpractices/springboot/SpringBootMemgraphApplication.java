package com.memgraph.bestpractices.springboot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Entry point for the Spring Boot + Spring Data Neo4j against Memgraph example.
 *
 * Nothing here is Memgraph-specific: a standard Spring Boot application that,
 * thanks to Memgraph's Bolt compatibility, talks to Memgraph instead of Neo4j.
 */
@SpringBootApplication
public class SpringBootMemgraphApplication {

    public static void main(String[] args) {
        SpringApplication.run(SpringBootMemgraphApplication.class, args);
    }
}
