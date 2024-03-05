import multiprocessing
import time
import subprocess
from time import sleep
from pathlib import Path
from neo4j import GraphDatabase
import sys

def process_chunk(query, create_list):
    try: 
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
        with driver.session() as session:
            session.run(query, {"batch": create_list})
        driver.close()
    except Exception as e:
        print("Failed to execute chunk: ", e)
        raise e

def run(size: str):

    CHUNK_SIZE = 10000
    FILE_PATH = ""

    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}")
    for file in Path(p).iterdir():
        if file.name.endswith(".nodes"):
            FILE_PATH = str(file)
            break

    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("", ""))

    with driver.session() as session:
        session.run("DROP INDEX ON :Node(id)")
        session.run("MATCH (n) DETACH DELETE n")
        sleep(1)
        session.run("CREATE INDEX ON :Node(id)")

    driver.close()

    query = """
    WITH $batch AS nodes
    UNWIND nodes AS node
    CREATE (n:Node {id:node.id})
    """

    chunks = []
    with open(FILE_PATH, "r") as file:
        create_nodes = []
        while True:
            line = file.readline()
            if not line:
                if len(create_nodes) > 0:
                    chunks.append(create_nodes)
                    print("Adding last chunk ...", len(create_nodes))
                    create_nodes = []
                break
            else:
                node_id = line.strip()
                create_nodes.append({"id": int(node_id)})
                if len(create_nodes) == CHUNK_SIZE:
                    print("Chunk size reached - adding to chunks ...", len(create_nodes))
                    chunks.append(create_nodes)
                    create_nodes = []
            
        res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
        megabytes_peak_RSS = round(int(res.stdout.split()[1])/1024, 2)
        print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

        print("Starting processing chunks...")
        start = time.time()
        with multiprocessing.Pool(10) as pool:
            pool.starmap(process_chunk, [(query, chunk) for chunk in chunks])
        end = time.time()
        print("Processing chunks finished in (wall time) ", end - start, " seconds")
        
        res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
        megabytes_peak_RSS = round(int(res.stdout.split()[1])/1024, 2)
        print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python concurrent_node_import.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size=size)