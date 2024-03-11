import multiprocessing
import mgclient
import time
import sys
from time import sleep
from pathlib import Path
import subprocess

HOST="127.0.0.1"
PORT=7687

def process_chunk(query, create_list):
    try: 
        conn = mgclient.connect(host=HOST, port=PORT)
        cursor = conn.cursor()
        cursor.execute(query, {"batch": create_list})
        conn.commit()
        conn.close()
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
     
    conn = mgclient.connect(host=HOST, port=PORT)
    sleep(1)

    if conn.status is mgclient.CONN_STATUS_READY:
        print("Connected to Memgraph")
    else:
        print("Connection status: %s" % conn.status)
        return
    cursor = conn.cursor()

    
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
        print("Usage: python concurrent_node_import.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size=size)
