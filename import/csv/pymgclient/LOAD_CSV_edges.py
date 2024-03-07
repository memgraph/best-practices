import mgclient
from time import sleep
import time
import subprocess
from pathlib import Path
import sys

HOST="127.0.0.1"
PORT=7687

def run(size: str):

    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/relationships.csv")

    subprocess.run(["docker", "cp", str(p), "memgraph:/usr/lib/memgraph/relationships.csv"], check=True)
   
    EDGES_FILE_PATH = "/usr/lib/memgraph/relationships.csv"

    conn = mgclient.connect(host=HOST, port=PORT)
    sleep(1)

    if conn.status is mgclient.CONN_STATUS_READY:
        print("Connected to Memgraph")
    else:
        print("Connection status: %s" % conn.status)
        return

    cursor = conn.cursor()

    conn.autocommit = False


    edge_query = """
    LOAD CSV FROM '/usr/lib/memgraph/relationships.csv' WITH HEADER AS row
    MATCH (source:Node {id: row.source}), (sink:Node {id: row.sink})
    CREATE (source)-[:RELATIONSHIP]->(sink)
    """
    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

    time_start = time.time()
    cursor.execute(edge_query)
    conn.commit()
    conn.close()
    time_end = time.time()

    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")
    
    print("Processing finished in ", time_end - time_start, " seconds")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python LOAD_CSV_edges.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)