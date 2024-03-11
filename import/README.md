# Import

In this directory, you'll find the best strategies for importing CSV and Cypher queries into Memgraph.

The cypher and csv folders contain examples of how to load a CYPHERL file and LOAD CSV via pymgclient and neo4jpython client. 

Before running any import script, make sure the `../dataset/graph500/download_dataset.sh` is executed first, 
It will pull all necessary data into the dataset directory needed to run the tests. 

If you are running a test, for example, the node import process in pymgclient, you need to pass the dataset size: 

```bash
python3 ./cypher/pymgclient/concurrent_node_import.py small
```

For concurrent LOAD CSV, Memgraph needs to be in `IN_MEMORY_ANALYTICAL` mode. 

## Test reference 

Below are the numbers representing import speed in different scenarios. The tests were run on the following hardware: 

CPU: AMD Ryzen 5 2600 Six-Core Processor
RAM: 2x8GB 2133 MT/s DDR4

All tests used ten concurrent database connections.

### Node import speed reference

Nodes per second = n/s
Peak memory pressure in megabytes = MB 

TEST 1: neo4jpython

| Storage mode             | Cypher seconds | Cypher n/s | Cypher MB | LOAD CSV seconds | LOAD CSV n/s | LOAD CSV MB |
|--------------------------|----------------|------------|-----------|------------------|--------------|-------------|
|  IN_MEMORY_TRANSACTIONAL |     0.560      |    311k    |   392     |      0.42        |    414k      |     230     |
|  IN_MEMORY_ANALYTICAL    |     0.461      |    377k    |   330     |      0.17        |    1.02M     |     140     |


TEST 2: pymgclient

| Storage mode             | Cypher seconds | Cypher n/s | Cypher MB | LOAD CSV seconds | LOAD CSV n/s | LOAD CSV MB |
|--------------------------|----------------|------------|-----------|------------------|--------------|-------------|
|  IN_MEMORY_TRANSACTIONAL |     0.443      |    393k    |   350     |      0.39        |    446k      |     203     |
|  IN_MEMORY_ANALYTICAL    |     0.350      |    497k    |   332     |      0.16        |    1.08M     |     142     |



## Edge import speed reference

Edges per second = e/s
Peak memory pressure in megabytes = MB 

Not possible = np

TEST 1: neo4jpython

| Storage mode             | Cypher seconds | Cypher e/s | Cypher MB | LOAD CSV seconds | LOAD CSV e/s | LOAD CSV MB |
|--------------------------|----------------|------------|-----------|------------------|--------------|-------------|
|  IN_MEMORY_TRANSACTIONAL |     166.20     |    45k     |   3772    |       np         |     np       |       np    |
|  IN_MEMORY_ANALYTICAL    |     22.99      |    330k    |   3235    |       6.30       |     1.2M     |     1132    |


TEST 2: pymgclient

| Storage mode             | Cypher seconds | Cypher e/s | Cypher MB | LOAD CSV seconds | LOAD CSV e/s | LOAD CSV MB |
|--------------------------|----------------|------------|-----------|------------------|--------------|-------------|
|  IN_MEMORY_TRANSACTIONAL |     101.34     |    75k     |   4299    |       np         |     np       |       np    |
|  IN_MEMORY_ANALYTICAL    |     14.78      |    514k    |   3421    |       6.28       |     1.2M     |     1125    |

