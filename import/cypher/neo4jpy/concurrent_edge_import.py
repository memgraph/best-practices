import multiprocessing
from time import sleep
import subprocess
import time
from pathlib import Path
from neo4j import GraphDatabase
from neo4j.exceptions import TransientError
import random
import sys

HOST_PORT = "bolt://localhost:7687"

#Option 1
def process_chunk_managed_API(query, create_list):
    driver = GraphDatabase.driver(HOST_PORT, auth=("", ""))
    with driver.session(max_transaction_retry_time=180.0, initial_retry_delay=0.2, retry_delay_multiplier=1.1, retry_delay_jitter_factor=0.1) as session:
        session.execute_write(lambda tx: tx.run(query, {"batch": create_list}))
    driver.close()

#Option 2
def process_chunk(query, create_list, max_retries=100, initial_wait_time=0.200, backoff_factor=1.1, jitter=0.1):
    session = GraphDatabase.driver(HOST_PORT, auth=("", "")).session()
    for attempt in range(max_retries):
        try:
            with session.begin_transaction() as tx:
                tx.run(query, {"batch": create_list})
                tx.commit()
                break
        except TransientError as te:
            jitter = random.uniform(0, jitter) * initial_wait_time 
            wait_time = initial_wait_time * (backoff_factor ** attempt) + jitter
            print(f"Commit failed on attempt {attempt+1}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Failed to execute transaction: {e}")
            session.close()
            raise e

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
    run()