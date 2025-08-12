const express = require("express");
const { ApolloServer } = require("apollo-server-express");
const neo4j = require("neo4j-driver");
const { Neo4jGraphQL } = require("@neo4j/graphql");
const dotenv = require("dotenv");
const jwt = require("jsonwebtoken");
const { typeDefs } = require("./graphql-schema");

dotenv.config();

const app = express();

// Ensure sessions/drivers created per request are closed
const cleanupPlugin = {
  async requestDidStart() {
    return {
      async willSendResponse({ context }) {
        try {
          if (context && context.executionContext && typeof context.executionContext.close === "function") {
            await context.executionContext.close();
          }
          if (context && context.__neo4jDriver && typeof context.__neo4jDriver.close === "function") {
            await context.__neo4jDriver.close();
          }
        } catch (_) {}
      },
    };
  },
};

let apolloServerConfiguration = {
  plugins: [cleanupPlugin],
  introspection: true,
  cache: "bounded",
};

if (process.env.APOLLO_PERSISTED_QUERIES === "false") {
  apolloServerConfiguration.persistedQueries = false;
}

const getBoltUrl = () => process.env.NEO4J_DOCKER || "bolt://localhost:7687";
const getDatabase = () => process.env.NEO4J_DATABASE || "memgraph";

let baseDriver = null;

if (process.env.NEO4J_AUTH === "true") {
  apolloServerConfiguration = {
    ...apolloServerConfiguration,
    context: ({ req }) => {
      const authHeader = (req.headers["authorization"] || "").toString();
      let userName = "";
      let password = "";
      if (authHeader.toLowerCase().startsWith("bearer ")) {
        const token = authHeader.slice(7);
        try {
          const decoded = jwt.decode(token) || {};
          userName = decoded.email || "";
          password = token;
        } catch (_) {}
      }
      const requestDriver = neo4j.driver(getBoltUrl(), neo4j.auth.basic(userName, password));
      const session = requestDriver.session({ database: getDatabase() });
      return {
        req,
        executionContext: session,
        __neo4jDriver: requestDriver,
      };
    },
  };
} else {
  baseDriver = neo4j.driver(
    getBoltUrl(),
    neo4j.auth.basic(process.env.NEO4J_USER || "", process.env.NEO4J_PASSWORD || "")
  );
  apolloServerConfiguration = {
    ...apolloServerConfiguration,
    context: () => {
      const session = baseDriver.session({ database: getDatabase() });
      return { executionContext: session };
    },
  };
}

const port = Number(process.env.GRAPHQL_LISTEN_PORT || 4001);
const path = process.env.GRAPHQL_SERVER_PATH || "/graphql";
const host = process.env.GRAPHQL_SERVER_HOST || "localhost";

const neo4jGraphQLOptions = {
  typeDefs,
  config: { enableRegex: true, driverConfig: { database: getDatabase() } },
};
if (baseDriver) {
  neo4jGraphQLOptions.driver = baseDriver;
}

const neo4jGraphQL = new Neo4jGraphQL(neo4jGraphQLOptions);

neo4jGraphQL
  .getSchema()
  .then((schema) => {
    apolloServerConfiguration.schema = schema;
    const server = new ApolloServer(apolloServerConfiguration);
    server.start().then(() => {
      server.applyMiddleware({ app, path });
      app.listen({ port }, () => {});
    });
  })
  .catch((err) => {
    console.error("Failed to start server:", err);
    process.exit(1);
  }); 