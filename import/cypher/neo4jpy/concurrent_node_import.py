import multiprocessing
import time
import subprocess
from time import sleep
from pathlib import Path
from neo4j import GraphDatabase

def process_chunk(query, create_list):
    print("Processing chunk...")
    node_chunk_execution_time = 0
    time_start = time.time()
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    with driver.session() as session:
        session.run(query, {"batch": create_list})
    time_end = time.time()
    node_chunk_execution_time = time_end - time_start
    print("Node chunk execution time: ", node_chunk_execution_time)
    return node_chunk_execution_time

def run():

    size = "small"
    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/graph500-scale18-ef16_adj.edges")
    FILE_PATH = str(p)
    CHUNK_SIZE = 10000

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

    with open(FILE_PATH, "r") as file:
        iteration = 0
        create_nodes = []
        nodes_set = set()
        chunks = []
        while True:
            line = file.readline()
            if not line:
                if len(create_nodes) > 0:
                    chunks.append(create_nodes)
                    create_nodes = []
                break
            else:
                iteration += 1

                node_sink, node_source = line.strip().split()  
                if node_source not in nodes_set:
                    create_nodes.append({"id": int(node_source)})
                    nodes_set.add(node_source)
                if node_sink not in nodes_set:
                    create_nodes.append({"id": int(node_sink)})
                    nodes_set.add(node_sink)

                if len(create_nodes) == CHUNK_SIZE:
                    print("Chunk size reached - adding to chunks ...", len(nodes_set))
                    chunks.append(create_nodes)
                    create_nodes = []

        res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
        megabytes_peak_RSS = int(res.stdout.split()[1])/1024
        print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")


        print("Starting processing chunks...")
        start = time.time()
        with multiprocessing.Pool(10) as pool:
            results = pool.starmap(process_chunk, [(query, chunk) for chunk in chunks])
            TOTAL_TIME = sum(results)
        end = time.time()
        print("Processing chunks finished in (wall time) ", end - start, " seconds")
        
        res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
        megabytes_peak_RSS = int(res.stdout.split()[1])/1024
        print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")

if __name__ == "__main__":
    run()