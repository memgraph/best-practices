import mgclient
from time import sleep
import time
import subprocess
import multiprocessing
from pathlib import Path


def execute_single_csv_file(query):
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    cursor = conn.cursor()
    time_start = time.time()
    cursor.execute(query)
    conn.commit()
    time_end = time.time()
    conn.close()
    return time_end - time_start


def run():
    
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    sleep(1)

    if conn.status is mgclient.CONN_STATUS_READY:
        print("Connected to Memgraph")
    else:
        print("Connection status: %s" % conn.status)
        return

    size = "small"
    target_nodes_directory = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/csv_node_chunks")
    for file in target_nodes_directory.glob("*.csv"):
        subprocess.run(["docker", "cp", str(file), f"memgraph:/usr/lib/memgraph/{file.name}"], check=True)
        
    queries = []
    for file in target_nodes_directory.glob("*.csv"):
        queries.append(f"LOAD CSV FROM '/usr/lib/memgraph/{file.name}' WITH HEADER AS row CREATE (n:Node {{id: row.id}})")
   
    cursor = conn.cursor()

    TOTAL_TIME = 0
    conn.autocommit = True
    cursor.execute("DROP INDEX ON :Node(id)")
    cursor.execute("MATCH (n) DETACH DELETE n")

    sleep(1)

    cursor.execute("CREATE INDEX ON :Node(id)")

    conn.autocommit = False

    conn.close()


    print("Starting processing different csv files...")


    
    res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = int(res.stdout.split()[1])/1024
    print("Peak memory usage before processing chunks: ", megabytes_peak_RSS, " MB")

    start = time.time()
    with multiprocessing.Pool(10) as pool:
        results = pool.starmap(execute_single_csv_file, [(q, ) for q in queries])
        TOTAL_TIME = sum(results)
    end = time.time()
    print("Processing chunks finished in (wall time) ", end - start, " seconds")

    res = subprocess.run(["docker", "exec", "-it", "memgraph", "grep", "^VmHWM", "/proc/1/status"], check=True, capture_output=True, text=True)
    megabytes_peak_RSS = int(res.stdout.split()[1])/1024
    print("Peak memory usage after processing chunks: ", megabytes_peak_RSS, " MB")
                    
    print("Total execution time: ", TOTAL_TIME)
        


if __name__ == "__main__":
    run()