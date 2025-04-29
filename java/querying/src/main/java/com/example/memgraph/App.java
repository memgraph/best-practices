package com.example.memgraph;

import org.neo4j.driver.AuthTokens;
import org.neo4j.driver.Driver;
import org.neo4j.driver.GraphDatabase;
import org.neo4j.driver.Session;
import org.neo4j.driver.Result;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

public class App {
    public static void main(String[] args) {
        if (args.length < 1) {
            System.err.println("Usage: java -jar app.jar <cypher_file_path>");
            System.exit(1);
        }

        String cypherFilePath = args[0];
        String uri = "bolt://localhost:7687";
        String user = ""; // Username (leave empty if no auth)
        String password = ""; // Password

        Driver driver = GraphDatabase.driver(uri, AuthTokens.basic(user, password));

        try (Session session = driver.session()) {
            session.run("STORAGE MODE IN_MEMORY_ANALYTICAL;");
            session.run("DROP GRAPH;");

            // Ingest from Cypher file
            System.out.println("Ingesting Cypher file...");
            var cypherLines = Files.readAllLines(Path.of(cypherFilePath));

            for (String line : cypherLines) {
                line = line.trim();
                if (!line.isEmpty() && !line.startsWith("//")) {
                    session.run(line);
                }
            }
            System.out.println("Ingestion complete.");

            String query = """
                        MATCH (start)
                        MATCH p=(start)-[:CONNECTED_TO * 1..6]-(end)
                        RETURN COUNT(DISTINCT end) AS cnt
                    """;

            long startTime = System.nanoTime();

            Result result = session.run(query);

            long endTime = System.nanoTime();
            long durationMillis = (endTime - startTime) / 1_000_000;

            System.out.println("DFS expansion results");
            while (result.hasNext()) {
                var record = result.next();
                System.out.println(record);
            }
            long streamingEndTime = System.nanoTime();
            long streamingDurationMillis = (streamingEndTime - startTime) / 1_000_000;

            System.out.println("Query executed in " + durationMillis + " ms.");
            System.out.println("Query streamed in " + streamingDurationMillis + " ms.");
        } catch (IOException e) {
            System.err.println("Failed to read Cypher file: " + e.getMessage());
        } finally {
            driver.close();
        }
    }
}
