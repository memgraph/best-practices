## Getting the dataset

In order to get a dataset locally on your machine, you need to run the `download_and_prep.sh` script with the `size` argument. Here is an example of downloading the dataset from the root folder: 

```bash
cd datasets/graph500/ 
./download_and_prep.sh small 
```

You can change the argument to currently supported sizes: 
- `small`: 174k nodes, 7.6M relationships
- `medium`: 1M nodes, 63M relationships
- `large`: 5M nodes, 259M relationships

The scripts will download the `.edges` file into the proper directory depending on the size argument. The `.edges` file will be split it to have unique `.nodes` and `.edges` in separate files. After that, the CSV files with nodes and relationships in `nodes.csv` and `relationship.csv` will be created. Each size will also have `csv_node_chunks` and `csv_relationship_chunks` directory that will split files into 10 chunks for concurrent CSV load tests. 


After running `download_and_prep.sh` you can start running tests.

Here is a sample call for concurrent node load via Cypher: 

```bash
cd ../..
python3 ./cypher/pymgclient/concurrent_node_import.py small
``````