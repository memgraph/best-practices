import mgclient
from time import sleep
import time
import subprocess
import multiprocessing
from pathlib import Path
import sys


def execute_csv_chunk(query):
    try: 
        conn = mgclient.connect(host='127.0.0.1', port=7687)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to execute transaction: {e}")
        raise e


def run(size: str):
    
    target_nodes_directory = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/csv_relationship_chunks")
    for file in target_nodes_directory.glob("*.csv"):
        subprocess.run(["docker", "cp", str(file), f"memgraph:/usr/lib/memgraph/{file.name}"], check=True)

    
    files = [f"/usr/lib/memgraph/relationships_{i}.csv" for i in range(0, 10)]
    queries = []
    for file in files:
        queries.append(
            f"""LOAD CSV FROM '{file}' WITH HEADER AS row
            MATCH (source:Node {{id: row.source}}), (sink:Node {{id: row.sink}})
            CREATE (source)-[:RELATIONSHIP]->(sink)
            """)
        
    print("Starting processing different csv files...")
    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

    start = time.time()
    with multiprocessing.Pool(10) as pool:
        pool.starmap(execute_csv_chunk, [(q, ) for q in queries])
    end = time.time()
    print("Processing chunks finished in ", end - start, " seconds")

    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")
        


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 concurrent_LOAD_CSV_edges.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size=size)
