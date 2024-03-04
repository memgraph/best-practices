import multiprocessing
import time
from time import sleep
import subprocess
from pathlib import Path
from neo4j import GraphDatabase
from neo4j.exceptions import TransientError
from neo4j.debug import watch
import random
import sys
import logging

#session._config.retry_delay_multiplier = 2.0
#session._config.retry_delay_jitter_factor=0.2
#session._config.max_transaction_retry_time=2000.0
#session.inital_retry_delay = 1.0
#TODO(antejavor): Test retry strategy

#this is not configurable
def execute_autocommit_implicit_API(query, create_list):
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    time_start = time.time()
    with driver.session(max_transaction_retry_time=180.0, initial_retry_delay=0.2, retry_delay_jitter_factor=1.1) as session:
        session.run(query, {"batch": create_list})
         
    driver.close()
    time_end = time.time()
    return time_end - time_start

def execute_managed_transaction_API(query, create_list):
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("", ""))
    time_start = time.time()
    with driver.session(max_transaction_retry_time=180.0, initial_retry_delay=0.2, retry_delay_multiplier=1.1) as session:
        session.execute_write(lambda tx: tx.run(query, {"batch": create_list}))
    driver.close()
    time_end = time.time()
    return time_end - time_start

def execute_explicit_transaction_API(query, create_list, max_retries=100, initial_wait_time=0.200, backoff_factor=1.1):
    session = GraphDatabase.driver("bolt://localhost:7687", auth=("", "")).session()
    time_start = time.time()
    for attempt in range(max_retries):
        try:
            with session.begin_transaction() as tx:
                tx.run(query, {"batch": create_list})
                tx.commit()
                break
        except TransientError as te:
            jitter = 0.1 * backoff_factor * random.random() 
            wait_time = initial_wait_time * (backoff_factor ** attempt) + jitter
            print(f"Commit failed on attempt {attempt+1}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Failed to execute transaction: {e}")
            break;
    session.close()
    time_end = time.time()
    return time_end - time_start


def process_chunk(query, create_nodes):
    print("Processing chunk...")
    edge_execution_time = execute_autocommit_implicit_API(query, create_nodes)
    print("Edge execution time: ", edge_execution_time)
    return edge_execution_time

def run():

    
    
    #TODO(antejavor): Parametrize the size and file name
    size = "small"

    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/graph500-scale18-ef16_adj.edges")
    FILE_PATH = str(p)
    CHUNK_SIZE = 50000
    TOTAL_TIME = 0


    query = """
    WITH $batch AS nodes
    UNWIND nodes AS node
    MATCH (a:Node {id: node.a}), (b:Node {id: node.b}) CREATE (a)-[:RELATIONSHIP]->(b)
    """


    with open(FILE_PATH, "r") as file:
        iteration = 0
        create_relationships = []
        chunks = []
        while True:
            line = file.readline()
            if not line:
                if len(create_relationships) > 0:
                    chunks.append(create_relationships)
                    create_relationships = []
                break
            else:
                node_sink, node_source = line.strip().split()  
                create_relationships.append({"a": int(node_source), "b": int(node_sink)})
                if len(create_relationships) == CHUNK_SIZE:
                    print("Chunk size reached - adding to chunks ...", len(create_relationships))
                    chunks.append(create_relationships)
                    create_relationships = []


        res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
        megabytes_peak_RSS = int(res.stdout.split()[1])/1024
        print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

        print("Starting processing chunks...")
        start = time.time()
        with multiprocessing.Pool(8) as pool:
            results = pool.starmap(process_chunk, [(query, chunk) for chunk in chunks])
            TOTAL_TIME = sum(results)
        end = time.time()
        print("Processing chunks finished in (wall time)  ", end - start, " seconds")


        res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
        megabytes_peak_RSS = int(res.stdout.split()[1])/1024
        print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")


    print("Total execution time: ", TOTAL_TIME)

if __name__ == "__main__":
    run()