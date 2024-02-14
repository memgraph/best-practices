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

    cursor = conn.cursor()

    #TODO(antejavor): Parametrize
    size = "small"
    p = Path(__file__).parents[3].joinpath(f"datasets/graph500/{size}/relationships.csv")

    #Copy the nodes.csv and relationships.csv files to the /usr/lib/memgraph/ directory
    subprocess.run(["docker", "cp", str(p), "memgraph:/usr/lib/memgraph/relationships.csv"], check=True)
   

    EDGES_FILE_PATH = "/usr/lib/memgraph/relationships.csv"
    TOTAL_TIME = 0
    conn.autocommit = True

    sleep(1)

    conn.autocommit = False

    edge_query = """
    LOAD CSV FROM '/usr/lib/memgraph/relationships.csv' WITH HEADER AS row
    MATCH (source:Node {id: row.source}), (sink:Node {id: row.sink})
    CREATE (source)-[:RELATIONSHIP]->(sink)
    """

    time_start = time.time()
    cursor.execute(edge_query)
    conn.commit()
    time_end = time.time()
    TOTAL_TIME += time_end - time_start

    print("Total execution time: ", TOTAL_TIME)

    conn.close()
    print("Connection closed")

if __name__ == "__main__":
    run()