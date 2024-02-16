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

    conn.close()
    size = "small"
    target_nodes_directory = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/csv_relationship_chunks")
    for file in target_nodes_directory.glob("*.csv"):
        subprocess.run(["docker", "cp", str(file), f"memgraph:/usr/lib/memgraph/{file.name}"], check=True)


    TOTAL_TIME = 0


    print("Starting processing different csv files...")
    files = [f"/usr/lib/memgraph/relationships_{i}.csv" for i in range(0, 10)]
    queries = []
    for file in files:
        queries.append(
            f"""LOAD CSV FROM '{file}' WITH HEADER AS row
            MATCH (source:Node {{id: row.source}}), (sink:Node {{id: row.sink}})
            CREATE (source)-[:RELATIONSHIP]->(sink)
            """)

    start = time.time()
    with multiprocessing.Pool(10) as pool:
        results = pool.starmap(execute_single_csv_file, [(q, ) for q in queries])
        TOTAL_TIME = sum(results)
    end = time.time()
    print("Processing chunks finished in ", end - start, " seconds")

                    
    print("Total execution time: ", TOTAL_TIME)
        


if __name__ == "__main__":
    run()