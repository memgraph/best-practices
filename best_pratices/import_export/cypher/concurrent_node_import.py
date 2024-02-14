import multiprocessing
import mgclient
import time
from time import sleep

def execute_singe_transaction_query(query, create_list):
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    cursor = conn.cursor()
    time_start = time.time()
    cursor.execute(query, {"batch": create_list})
    conn.commit()
    time_end = time.time()
    conn.close()
    return time_end - time_start

def process_chunk(query, create_nodes):
    print("Processing chunk...")
    node_execution_time = execute_singe_transaction_query(query, create_nodes)
    print("Node execution time: ", node_execution_time)
    return node_execution_time

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
    CHUNK_SIZE = 10000
    TOTAL_TIME = 0
    conn.autocommit = True
    cursor.execute("DROP INDEX ON :Node(id)")
    cursor.execute("MATCH (n) DETACH DELETE n")
    sleep(1)

    cursor.execute("CREATE INDEX ON :Node(id)")

    conn.autocommit = False

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
        print("Starting processing chunks...")
        start = time.time()
        with multiprocessing.Pool(10) as pool:
            results = pool.starmap(process_chunk, [(query, chunk) for chunk in chunks])
            TOTAL_TIME = sum(results)
        end = time.time()
        print("Processing chunks finished in ", end - start, " seconds")



    print("Total execution time: ", TOTAL_TIME)

if __name__ == "__main__":
    run()