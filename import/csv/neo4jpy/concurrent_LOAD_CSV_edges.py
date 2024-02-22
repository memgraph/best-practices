
from time import sleep
import time
from neo4j import GraphDatabase
import subprocess
import multiprocessing
from pathlib import Path


def execute_single_csv_file(query):
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    time_start = time.time()
    with driver.session() as session:
        session.run(query)
    time_end = time.time()
    return time_end - time_start


def run():
    

    size = "small"
    target_nodes_directory = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/csv_relationship_chunks")
    for file in target_nodes_directory.glob("*.csv"):
        subprocess.run(["docker", "cp", str(file), f"memgraph:/usr/lib/memgraph/{file.name}"], check=True)


    TOTAL_TIME = 0


    print("Starting processing different csv files...")
    files = [f"/usr/lib/memgraph/relationships_{i}.csv" for i in range(0, 10)]
    queries = []
    for file in files:
        queries.append(
            f"""LOAD CSV FROM '{file}' WITH HEADER AS row
            MATCH (source:Node {{id: row.source}}), (sink:Node {{id: row.sink}})
            CREATE (source)-[:RELATIONSHIP]->(sink)
            """)
        
    res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = int(res.stdout.split()[1])/1024
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

    start = time.time()
    with multiprocessing.Pool(10) as pool:
        results = pool.starmap(execute_single_csv_file, [(q, ) for q in queries])
        TOTAL_TIME = sum(results)
    end = time.time()
    print("Processing chunks finished in (wall time) ", end - start, " seconds")

    res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = int(res.stdout.split()[1])/1024
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")
                    
    print("Total execution time: ", TOTAL_TIME)
        


if __name__ == "__main__":
    run()