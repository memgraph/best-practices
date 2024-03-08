# Import

In this directory you'll find the best strategies to import CSV and Cypher queries into Memgraph.

Under cypher and csv folders, are examples of how to load CYPHERL file and LOAD CSV via pymgclient and neo4jpython client. 

Before running any import script, make sure the `../dataset/graph500/download_dataset.sh` is executed first, 
it will pull all necessary data into the dataset directory needed for running the tests. 

If you are running a test, for example node import proces in pymgclinet, you need to pass the dataset size: 

```bash
python3 ./cypher/pymgclient/concurrent_node_import.py small
```

For concurrent LOAD CSV, Memgraph needs to be in `IN_MEMORY_ANALYTICAL` mode. 

## Node import speed reference

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
|  IN_MEMORY_TRANSACTIONAL |     0.560      |    311k    |   392     |      0.42        |    414k      |     230     |
|  IN_MEMORY_ANALYTICAL    |     0.461      |    377k    |   330     |      0.17        |    1.02M     |     140     |


TEST 3: 
TBD



## Edge import speed reference

Edges per second = e/s
Peak memory pressure in megabytes = MB 

Not possible = np

TEST 1: 

| Storage mode             | Cypher seconds | Cypher e/s | Cypher MB | LOAD CSV seconds | LOAD CSV e/s | LOAD CSV MB |
|--------------------------|----------------|------------|-----------|------------------|--------------|-------------|
|  IN_MEMORY_TRANSACTIONAL |     166.20     |    45k     |   3772    |       np         |     np       |       np    |
|  IN_MEMORY_ANALYTICAL    |     22.99      |    330k    |   3235    |       6.3        |     1.2M     |     1132    |


TEST 2:
TBD


TEST 3: 
TBD