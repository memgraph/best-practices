import mgclient
from time import sleep
import time
import subprocess
from pathlib import Path


def run():
    
    conn = mgclient.connect(host='127.0.0.1', port=7687)
    sleep(1)

    if conn.status is mgclient.CONN_STATUS_READY:
        print("Connected to Memgraph")
    else:
        print("Connection status: %s" % conn.status)
        return

    size = "small"
    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/nodes.csv")

    subprocess.run(["docker", "cp", str(p), "memgraph:/usr/lib/memgraph/nodes.csv"], check=True)
    cursor = conn.cursor()

    FILE_PATH = "/usr/lib/memgraph/nodes.csv"
    TOTAL_TIME = 0
    conn.autocommit = True
    cursor.execute("DROP INDEX ON :Node(id)")
    cursor.execute("MATCH (n) DETACH DELETE n")

    sleep(1)

    cursor.execute("CREATE INDEX ON :Node(id)")

    conn.autocommit = False

    query = query = """
    LOAD CSV FROM '/usr/lib/memgraph/nodes.csv' WITH HEADER AS row
    CREATE (n:Node {id: row.id})
    """

    time_start = time.time()
    cursor.execute(query)
    conn.commit()
    time_end = time.time()
    TOTAL_TIME += time_end - time_start

                    
    print("Total execution time: ", TOTAL_TIME)
        

    conn.close()
    print("Connection closed")



if __name__ == "__main__":
    run()