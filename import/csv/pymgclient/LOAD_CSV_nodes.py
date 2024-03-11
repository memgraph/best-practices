import mgclient
from time import sleep
import time
import subprocess
from pathlib import Path
import sys

HOST="127.0.0.1"
PORT=7687

def run(size: str):


    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/nodes.csv")

    subprocess.run(["docker", "cp", str(p), "memgraph:/usr/lib/memgraph/nodes.csv"], check=True)

    FILE_PATH = "/usr/lib/memgraph/nodes.csv"
        
    conn = mgclient.connect(host=HOST, port=PORT)
    sleep(1)

    if conn.status is mgclient.CONN_STATUS_READY:
        print("Connected to Memgraph")
    else:
        print("Connection status: %s" % conn.status)
        return
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DROP INDEX ON :Node(id)")
    cursor.execute("MATCH (n) DETACH DELETE n")

    sleep(1)

    cursor.execute("CREATE INDEX ON :Node(id)")

    conn.autocommit = False

    query = """
    LOAD CSV FROM '/usr/lib/memgraph/nodes.csv' WITH HEADER AS row
    CREATE (n:Node {id: row.id})
    """
    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")
    time_start = time.time()
    cursor.execute(query)
    conn.commit()
    conn.close()
    time_end = time.time()

    print("Processing finished in ", time_end - time_start, " seconds")
          
    memory = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = round(int(memory.stdout.split()[1])/1024, 2)
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")
        



if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 LOAD_CSV_nodes.py <size>")
        sys.exit(1)
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)
