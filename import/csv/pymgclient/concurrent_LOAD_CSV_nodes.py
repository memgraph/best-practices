import mgclient
from time import sleep
import time
import subprocess
import multiprocessing
from pathlib import Path
import sys

HOST="127.0.0.1"
PORT=7687

def execute_csv_chunk(query):
    try:
        conn = mgclient.connect(host=HOST, port=PORT)
        cursor = conn.cursor()
        cursor.execute(query)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to execute transaction: {e}")
        raise e


def run(size : str):
    
    target_nodes_directory = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/csv_node_chunks")
    for file in target_nodes_directory.glob("*.csv"):
        subprocess.run(["docker", "cp", str(file), f"memgraph:/usr/lib/memgraph/{file.name}"], check=True)
        
    queries = []
    for file in target_nodes_directory.glob("*.csv"):
        queries.append(f"LOAD CSV FROM '/usr/lib/memgraph/{file.name}' WITH HEADER AS row CREATE (n:Node {{id: row.id}})")
   

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

    conn.close()


    print("Starting processing different csv files...")

    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

    start = time.time()
    with multiprocessing.Pool(10) as pool: 
        pool.starmap(execute_csv_chunk, [(q, ) for q in queries])
    end = time.time()
    print("Processing chunks finished in (wall time) ", end - start, " seconds")


    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python concurrent_LOAD_CSV_nodes.py <size>")
        sys.exit(1) 
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size=size)
