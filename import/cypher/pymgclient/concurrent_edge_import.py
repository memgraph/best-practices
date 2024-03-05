import multiprocessing
import mgclient
import time
import subprocess
from time import sleep
import random
import sys
from pathlib import Path

def process_chunk(query, create_list, max_retries=100, initial_wait_time=0.200, backoff_factor=1.1, jitter=0.1):
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    cursor = conn.cursor()
    for attempt in range(max_retries):
        try:
            cursor.execute(query, {"batch": create_list})
            conn.commit()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed to execute transaction: {e}")
                raise e
            else: 
                jitter = random.uniform(0, jitter) * initial_wait_time
                wait_time = initial_wait_time * (backoff_factor ** attempt) + jitter
                print(f"Commit failed on attempt {attempt+1}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)

def run(size: str):

    FILE_PATH = ""
    CHUNK_SIZE = 50000
    
    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}")
    for file in Path(p).iterdir():
        if file.name.endswith(".edges"):
            FILE_PATH = str(file)
            break

    query = """
    WITH $batch AS nodes
    UNWIND nodes AS node
    MATCH (a:Node {id: node.a}), (b:Node {id: node.b}) CREATE (a)-[:RELATIONSHIP]->(b)
    """

    chunks = []
    with open(FILE_PATH, "r") as file:
        create_relationships = []
        chunks = []
        while True:
            line = file.readline()
            if not line:
                if len(create_relationships) > 0:
                    chunks.append(create_relationships)
                    print("Adding last chunk ...", len(create_relationships))
                    break
            else:
                node_sink, node_source = line.strip().split()  
                create_relationships.append({"a": int(node_source), "b": int(node_sink)})
                if len(create_relationships) == CHUNK_SIZE:
                    print("Chunk size reached - adding to chunks ...", len(create_relationships))
                    chunks.append(create_relationships)
                    create_relationships = []

    
    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

    print("Starting processing chunks...")
    start = time.time()
    with multiprocessing.Pool(10) as pool:
        pool.starmap(process_chunk, [(query, chunk) for chunk in chunks])
    end = time.time()
    print("Processing chunks finished in ", end - start, " seconds")

    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python concurrent_edge_import.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)