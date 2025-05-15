from gqlalchemy import Memgraph
import time
import os

memgraph = Memgraph(host="127.0.0.1", port=7687)

# Define the dataset path
DATASET_PATH = os.path.join("datasets", "energy-management-memgraph-lab", "energy-management-system.cypherl")


def read_cypherl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        # Each line is a separate query
        return [line.strip() for line in file if line.strip()]


def execute_queries(memgraph: Memgraph, queries: list):
    for query in queries:
        memgraph.execute(query)


def execute_explain_profile_query(title: str, query: str, use_profile: bool = False):
    print(f"\n{title}")
    print("-" * 80)
    
    # Add EXPLAIN or PROFILE to the query
    prefix = "PROFILE" if use_profile else "EXPLAIN"
    full_query = f"{prefix} {query}"
    
    start = time.time()
    result = list(memgraph.execute_and_fetch(full_query))
    end = time.time()
    
    # Print the query plan
    for row in result:
        print(row)
    
    print(f"\nQuery executed in {end - start:.4f}s")
    print("-" * 80)


def main():
    # Step 1: Switch to analytical mode
    print("🔄 Switching to analytical mode...")
    memgraph.execute("STORAGE MODE IN_MEMORY_ANALYTICAL;")

    # Step 2: Drop the graph
    print("🗑️ Dropping existing graph...")
    memgraph.execute("DROP GRAPH;")

    # Step 3: Read and execute the queries
    print(f"📖 Reading dataset from {DATASET_PATH}...")
    queries = read_cypherl_file(DATASET_PATH)
    execute_queries(memgraph, queries)
    print("✅ All queries executed successfully.")
    print()

    # Example 1: Simple MATCH query with EXPLAIN
    execute_explain_profile_query(
        "Example 1: EXPLAIN for simple MATCH query",
        "MATCH (n:Generator) RETURN n LIMIT 5"
    )

    # Example 2: Same query with PROFILE
    execute_explain_profile_query(
        "Example 2: PROFILE for simple MATCH query",
        "MATCH (n:Generator) RETURN n LIMIT 5",
        use_profile=True
    )

    # Example 3: Complex query with EXPLAIN
    execute_explain_profile_query(
        "Example 3: EXPLAIN for complex query with multiple operations",
        """
        MATCH (g:Generator)-[:CONNECTED_TO]->(connected:Generator)
        WHERE g.id = 90
        WITH g, collect(connected) as connected_generators
        MATCH (c:Generator)-[:CONNECTED_TO]->(d:Generator)
        WHERE c IN connected_generators
        RETURN d.id as target_generator, count(*) as connection_count
        ORDER BY connection_count DESC
        """
    )

    # Example 4: Same complex query with PROFILE
    execute_explain_profile_query(
        "Example 4: PROFILE for complex query with multiple operations",
        """
        MATCH (g:Generator)-[:CONNECTED_TO]->(connected:Generator)
        WHERE g.id = 90
        WITH g, collect(connected) as connected_generators
        MATCH (c:Generator)-[:CONNECTED_TO]->(d:Generator)
        WHERE c IN connected_generators
        RETURN d.id as target_generator, count(*) as connection_count
        ORDER BY connection_count DESC
        """,
        use_profile=True
    )

    # Example 5: Query with index usage EXPLAIN
    execute_explain_profile_query(
        "Example 5: EXPLAIN for query using index",
        "MATCH (g:Generator {id: 90}) RETURN g"
    )

    # Example 6: Same query with PROFILE
    execute_explain_profile_query(
        "Example 6: PROFILE for query using index",
        "MATCH (g:Generator {id: 90}) RETURN g",
        use_profile=True
    )


if __name__ == "__main__":
    main() 