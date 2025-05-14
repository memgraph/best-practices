import multiprocessing
import os
import time
from gqlalchemy import Memgraph

# Function to run a Cypher file using gqlalchemy
def run_cypher_file(cypher_file):
    # Establish a connection to Memgraph using gqlalchemy
    memgraph = Memgraph(host='127.0.0.1', port=7687)

    try:
        # Open the Cypher file and read it line by line
        with open(cypher_file, "r") as f:
            for line in f:
                line = line.strip()  # Remove any surrounding whitespace or newlines
                if line:  # Ensure the line isn't empty
                    # Debugging: Print the query to verify its contents
                    print(f"Executing query: {line}")
                    
                    # Execute each Cypher query using gqlalchemy
                    result = list(memgraph.execute_and_fetch(line))
                    print(f"Query executed successfully: {line}")
                    # Optional: print the result for debugging
                    print(f"Result: {result}")
                else:
                    print(f"Skipping empty line in file {cypher_file}")
    except Exception as e:
        print(f"Error executing queries in {cypher_file}: {str(e)}")

# Run queries in parallel using multiprocessing
def run_in_parallel(cypher_files):
    processes = []
    for cypher_file in cypher_files:
        process = multiprocessing.Process(target=run_cypher_file, args=(cypher_file,))
        processes.append(process)
        process.start()

    # Wait for all processes to finish
    for process in processes:
        process.join()

if __name__ == "__main__":
    # Record the start time before execution begins
    start_time = time.time()

    # List of node Cypher files to run in parallel
    node_files = [f"split_queries/nodes_part_{i+1}.cypher" for i in range(8)]

    # Run node creation queries in parallel
    run_in_parallel(node_files)

    # List of relationship Cypher files to run in parallel
    relationship_files = [f"split_queries/relationships_part_{i+1}.cypher" for i in range(8)]

    # Run relationship creation queries in parallel
    run_in_parallel(relationship_files)

    # Record the end time after execution finishes
    end_time = time.time()

    # Calculate the time taken
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
