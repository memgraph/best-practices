import multiprocessing
import subprocess
import os
import time  # Import the time module

# Function to run a Cypher file using mgconsole with input redirection
def run_cypher_file(cypher_file):
    command = f"mgconsole < {cypher_file}"
    try:
        # Print the command being executed
        print(f"Running {cypher_file} using: {command}")
        
        # Execute the command with input redirection in shell
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Print the output and errors (for debugging)
        print(f"Process {multiprocessing.current_process().name} executed successfully: {cypher_file}")
        print(f"Output: {result.stdout.decode()}")
        print(f"Errors: {result.stderr.decode()}")
    except subprocess.CalledProcessError as e:
        print(f"Process {multiprocessing.current_process().name} failed: {e.stderr.decode()}")

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
