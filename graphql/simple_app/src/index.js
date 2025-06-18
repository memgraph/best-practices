const { Neo4jGraphQL } = require("@neo4j/graphql");
const { ApolloServer } = require('@apollo/server');
const { startStandaloneServer } = require('@apollo/server/standalone');
const neo4j = require('neo4j-driver');
const typeDefs = require('./schema');

// Neo4j driver configuration
const driver = neo4j.driver("bolt://localhost:7687",
    neo4j.auth.basic("", ""),
    {
        maxConnectionLifetime: 3 * 60 * 60 * 1000, // 3 hours
        maxConnectionPoolSize: 50,
        connectionAcquisitionTimeout: 30000, // 30 seconds
        disableLosslessIntegers: true
    }
);

// Create Neo4j GraphQL instance
const neoSchema = new Neo4jGraphQL({ 
    typeDefs, 
    driver,
    config: {
        driverConfig: {
            database: "memgraph"
        }
    }
});

// Start the server
const startServer = async () => {
    try {
        // Generate the schema
        const schema = await neoSchema.getSchema();

        // Create Apollo Server
        const server = new ApolloServer({
            schema,
            formatError: (error) => {
                console.error('GraphQL Error:', error);
                return {
                    message: error.message,
                    path: error.path,
                    extensions: {
                        code: error.extensions?.code || 'INTERNAL_SERVER_ERROR'
                    }
                };
            }
        });

        const { url } = await startStandaloneServer(server, {
            context: async ({ req }) => ({ 
                req, 
                sessionConfig: { database: "memgraph" },
                cypherQueryOptions: { addVersionPrefix: false }
            }),
            listen: { port: 4000 },
        });
        console.log(`🚀 Server ready at ${url}`);
        console.log(`📚 GraphQL API documentation available at ${url}/graphql`);
    } catch (error) {
        console.error('Error starting server:', error);
        process.exit(1);
    }
};

// Handle process termination
process.on('SIGINT', async () => {
    console.log('Shutting down server...');
    await driver.close();
    process.exit(0);
});

startServer(); 
