# Spring Boot + Spring Data Neo4j with Memgraph

This example shows that a **Spring Boot** application built with **Spring Data
Neo4j** works as a **drop-in replacement** against Memgraph. Memgraph speaks the
Bolt protocol and is wire-compatible with the Neo4j Java driver, so the only
thing that changes versus a Neo4j project is the connection URI.

It is modeled on the official
[Spring Data Neo4j getting-started guide](https://neo4j.com/docs/getting-started/languages-guides/java/spring-data-neo4j/)
and reuses the same `Movie` / `Person` domain so you can compare them side by side.

## 🧠 What This Example Does

1. Connects Spring Data Neo4j to Memgraph over Bolt (`bolt://localhost:7687`).
2. Maps `:Movie` and `:Person` nodes (and the `ACTED_IN` / `DIRECTED`
   relationships) with the standard `@Node`, `@Id`, `@Property` and
   `@Relationship` annotations.
3. On startup, [SchemaInitializer.java](src/main/java/com/memgraph/bestpractices/springboot/SchemaInitializer.java)
   creates label indexes (`:Movie`, `:Person`) and label-property indexes
   (`:Movie(title)`, `:Person(name)`), then a
   `CommandLineRunner` ([DataLoader.java](src/main/java/com/memgraph/bestpractices/springboot/DataLoader.java))
   **loads** a small movie graph and **queries** it — both a derived query and an
   explicit `@Query` Cypher statement.
4. Exposes a small REST API ([MovieController.java](src/main/java/com/memgraph/bestpractices/springboot/controllers/MovieController.java))
   to load and query data over HTTP.

## 📦 Project Structure

```
src/main/java/com/memgraph/bestpractices/springboot/
├── SpringBootMemgraphApplication.java   # Spring Boot entry point
├── SchemaInitializer.java               # creates indexes on startup
├── DataLoader.java                      # loads + queries data on startup
├── entities/
│   ├── MovieEntity.java
│   └── PersonEntity.java
├── repositories/
│   └── MovieRepository.java
└── controllers/
    └── MovieController.java
src/main/resources/
└── application.properties               # <-- the only Memgraph-specific config
```

## 🚀 How to Run Memgraph

A [`docker-compose.yml`](./docker-compose.yml) is provided with Memgraph (MAGE)
and Memgraph Lab:

```bash
docker compose up -d
```

This starts Memgraph on Bolt port `7687` and Memgraph Lab on
[http://localhost:3000](http://localhost:3000).

Prefer a single container? You can also run:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph-mage:3.10.1
```

## 🛠 Requirements

- **Java 17+** (set in [`pom.xml`](./pom.xml) via `java.version`)
- **Maven 3.6+** (or use the Maven wrapper if you generate one)

Dependencies are declared in [`pom.xml`](./pom.xml) — the standard Spring Boot
starters `spring-boot-starter-data-neo4j` and `spring-boot-starter-web`. No
Memgraph-specific library is needed.

## 🧪 How to Run the App

1. Start Memgraph: `docker compose up -d`
2. Run the app: `mvn spring-boot:run`

On startup you should see log lines like:

```
Loaded 1 movie(s) into Memgraph
Found movie 'The Matrix' with 2 actor(s) and tagline "Welcome to the Real World"
Keanu Reeves acted in: The Matrix
```

### Try the REST API

```bash
# List all movies
curl http://localhost:8080/movies

# Fetch one movie by title
curl "http://localhost:8080/movies/by-title?title=The%20Matrix"

# Movies a given actor played in
curl "http://localhost:8080/movies/by-actor?name=Keanu%20Reeves"

# Create / update a movie
curl -X PUT http://localhost:8080/movies \
  -H "Content-Type: application/json" \
  -d '{"title":"John Wick","description":"People keep asking if I am back"}'

# Delete a movie by title
curl -X DELETE "http://localhost:8080/movies/John%20Wick"
```

## 🔁 Migrating an existing Neo4j project

The whole point: switching a Spring Data Neo4j app from Neo4j to Memgraph is a
config change. In [`application.properties`](src/main/resources/application.properties):

```properties
# Neo4j Aura
spring.neo4j.uri=neo4j+s://<instance>.databases.neo4j.io

# Memgraph
spring.neo4j.uri=bolt://localhost:7687
```

A few Memgraph-specific notes:

- **Authentication is off by default** in Memgraph, so the username/password
  properties are left blank. Fill them in if you created a user.
- **Do not set `spring.data.neo4j.database`.** Memgraph has a single database;
  setting it makes the driver issue `USE <db>`, which Memgraph rejects.
- Prefer an **assigned business key** for `@Id` (here `title` / `name`) rather
  than relying on internal node ids.
- **Create indexes** — Memgraph creates none out of the box. You need both a
  **label index** (`CREATE INDEX ON :Movie`) so plain `MATCH (m:Movie)` scans
  from `findAll`/`count`/`deleteAll` don't sweep the whole store, and a
  **label-property index** (`CREATE INDEX ON :Movie(title)`) for the `@Id`
  lookups SDN's generated Cypher uses. Without them you'll see `PlanHinting`
  sequential-scan warnings. This example creates both automatically in
  [SchemaInitializer.java](src/main/java/com/memgraph/bestpractices/springboot/SchemaInitializer.java).

## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph v3.10.1** (`memgraph/memgraph-mage:3.10.1`)
- **Spring Boot 3.3.4** / **Spring Data Neo4j 7.3.4**
- **Java 17**

> ⚠️ Use Memgraph **3.10.1 or newer**. On older versions (e.g. 3.2) the
> relationship-persistence query that Spring Data Neo4j generates could
> terminate the server connection — this was verified fixed on 3.10.1.

If you run into any issues or have questions, feel free to reach out on the
[Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!

## 🏢 Enterprise or Community?

> ✅ This example **runs on Memgraph Community Edition**.
