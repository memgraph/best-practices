from gqlalchemy import Memgraph
import sys
import time

memgraph = Memgraph(host="127.0.0.1", port=7687)


def read_cypherl_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        # Each line is a separate query
        return [line.strip() for line in file if line.strip()]


def execute_queries(memgraph: Memgraph, queries: list):
    for query in queries:
        memgraph.execute(query)


def execute_path_query(title: str, query: str):
    start = time.time()
    print(title)
    result = list(memgraph.execute_and_fetch(query))
    end = time.time()
    print(result)
    print(f"Query executed and and streamed in {end - start}s")
    print()


def main():
    if len(sys.argv) != 2:
        print("Usage: python ingest_to_memgraph.py path/to/queries.cypherl")
        sys.exit(1)

    cypherl_file_path = sys.argv[1]

    # Step 1: Switch to analytical mode
    print("🔄 Switching to analytical mode...")
    memgraph.execute("STORAGE MODE IN_MEMORY_ANALYTICAL;")

    # Step 2: Drop the graph
    print("🗑️ Dropping existing graph...")
    memgraph.execute("DROP GRAPH;")

    # Step 3: Read and execute the queries
    queries = read_cypherl_file(cypherl_file_path)
    execute_queries(memgraph, queries)
    print("✅ All queries executed successfully.")
    print()

    # Step 4: Path traversals

    ## Example 1:
    ## wShortest -> shortest path between 2 points
    ## (r, n | 1) -> will apply cost of each traversal as 1
    execute_path_query(
        "Example 1: Executing shortest path between 2 points",
        "MATCH p=(start:Generator {id: 90})-[:CONNECTED_TO *wShortest (r, n | 1)]-(end:Generator {id: 7072}) RETURN start, end, size(p) as path_length",
    )
    
    ## Example 2:
    ## DFS -> returning all the paths between 2 points
    ## This particular query will expand to all the paths from source to any target generator in 15 hops
    execute_path_query(
        "Example 2: Executing all paths from source for 15 hops",
        "MATCH p=(start:Generator {id: 90})-[:CONNECTED_TO *1..15]-(end:Generator) RETURN count(p) as number_of_paths",
    )

    ## Example 3:
    ## BFS -> returning 1 path per source - target pair
    ## This particular query will expand to all the generators -> use it when trying to figure out all the reachable nodes
    ## Faster than DFS because it doesn't do all paths
    execute_path_query(
        "Example 3 (WORKAROUND FOR EXAMPLE 4): Finding all reachable nodes from source for 15 hops",
        """
            MATCH p=(start:Generator {id: 90})-[:CONNECTED_TO *BFS 1..15]-(end)
            WITH p, start, end
            WHERE end:Generator
            RETURN count(p) as number_of_paths
        """,
    )

    ## Example 4:
    ## BFS -> NOT OPTIMIZED EXAMPLE!
    ## This particular example is the same thing but it will take longer because planner is not optimized for this specific
    ## scenario
    ## Rather use the previous example (Example 3)
    execute_path_query(
        "Example 4 (NOT OPTIMIZED): Finding all reachable nodes from source for 15 hops",
        """
            MATCH p=(start:Generator {id: 90})-[:CONNECTED_TO *BFS 1..15]-(end:Generator)
            RETURN count(p) as number_of_paths
        """,
    )
    
    ## Example 5:
    ## BFS -> inline filtering that reduces the search space and is more optimized
    ## This particular query will expand to all the generators -> use it when trying to figure out all the reachable nodes
    ## Additionally, during the traversal it will apply the logic to only use generators whose ID is less than 1000
    execute_path_query(
        "Example 5: Finding all reachable nodes from source for 15 hops with inline filtering",
        """
            MATCH p=(start:Generator {id: 90})-[:CONNECTED_TO *BFS 1..15 (r, n | n.id < 1000)]-(end)
            WITH p, start, end
            WHERE end:Generator
            RETURN count(p) as number_of_paths
        """,
    )
    
    ## Example 6:
    ## wShortest -> shortest path between 2 points with cost function
    ## (r, n | n.id) -> will apply cost of each traversal based on the id of the generator
    ## You can also retrieve the cost of the path by applying the variable after the cost function
    execute_path_query(
        "Example 1: Executing shortest path between 2 points",
        "MATCH p=(start:Generator {id: 90})-[:CONNECTED_TO *wShortest (r, n | n.id) total_cost]-(end:Generator {id: 7072}) RETURN start, end, size(p) as path_length, total_cost",
    )


if __name__ == "__main__":
    main()
