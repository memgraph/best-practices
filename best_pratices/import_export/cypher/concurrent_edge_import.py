import multiprocessing
import mgclient
import time
from time import sleep
import random

def execute_singe_transaction_query(query, create_list, max_retries=100, initial_wait_time=0.200, backoff_factor=1.1):
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    cursor = conn.cursor()
    time_start = time.time()
    for attempt in range(max_retries):
        try:
            cursor.execute(query, {"batch": create_list})
            conn.commit()
            break
        except Exception as e:
            wait_time = initial_wait_time * (backoff_factor ** attempt)
            print(f"Commit failed on attempt {attempt+1}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    else:
        print("Max retries reached. Commit failed.")
        conn.close()
        return time.time() - time_start
    time_end = time.time()
    conn.close()
    return time_end - time_start

def process_chunk(query, create_nodes):
    print("Processing chunk...")
    edge_execution_time = execute_singe_transaction_query(query, create_nodes)
    print("Edge execution time: ", edge_execution_time)
    return edge_execution_time

def run():
     
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    sleep(1)

    if conn.status is mgclient.CONN_STATUS_READY:
        print("Connected to Memgraph")
    else:
        print("Connection status: %s" % conn.status)
        return
    cursor = conn.cursor()
    FILE_PATH = "../datasets/graph500/small/graph500-scale18-ef16_adj.edges"
    CHUNK_SIZE = 50000
    TOTAL_TIME = 0
    # conn.autocommit = True
    # cursor.execute("DROP INDEX ON :Node(id)")
    # cursor.execute("MATCH (n) DETACH DELETE n")
    sleep(1)

    # cursor.execute("CREATE INDEX ON :Node(id)")

    
    conn.autocommit = False

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

        print("Starting processing chunks...")
        start = time.time()
        with multiprocessing.Pool(8) as pool:
            results = pool.starmap(process_chunk, [(query, chunk) for chunk in chunks])
            TOTAL_TIME = sum(results)
        end = time.time()
        print("Processing chunks finished in ", end - start, " seconds")



    print("Total execution time: ", TOTAL_TIME)

if __name__ == "__main__":
    run()