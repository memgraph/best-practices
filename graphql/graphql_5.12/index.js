const express = require("express");
const { ApolloServer } = require("apollo-server-express");
const neo4j = require("neo4j-driver");
const { Neo4jGraphQL } = require("@neo4j/graphql");
const { typeDefs } = require("./graphql-schema");

const app = express();

let apolloServerConfiguration = {
  introspection: true,
  cache: "bounded",
  persistedQueries: false,
};

const getBoltUrl = () => "bolt://localhost:7687";
const getDatabase = () => "memgraph";

let baseDriver = neo4j.driver(
  getBoltUrl(),
  neo4j.auth.basic("", "")
);

apolloServerConfiguration = {
  ...apolloServerConfiguration,
  context: ({ req }) => ({
    req,
    driver: baseDriver,
    sessionConfig: { database: getDatabase() },
  }),
};

const neo4jGraphQLOptions = {
  typeDefs,
  config: { enableRegex: true, driverConfig: { database: getDatabase() } },
  driver: baseDriver,
};

const neo4jGraphQL = new Neo4jGraphQL(neo4jGraphQLOptions);

const port = 4001;
const path = "/graphql";

neo4jGraphQL
  .getSchema()
  .then((schema) => {
    apolloServerConfiguration.schema = schema;
    const server = new ApolloServer(apolloServerConfiguration);
    server.start().then(() => {
      server.applyMiddleware({ app, path });
      app.listen({ port }, () => { });
    });
  })
  .catch((err) => {
    console.error("Failed to start server:", err);
    process.exit(1);
  }); 