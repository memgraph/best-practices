## Getting the dataset

In order to get a dataset locally on your machine, you need to run the `download_and_prep.sh` script with the `size` argument. Here is an example of downloading the dataset from the root folder: 

```bash
cd datasets/graph500/ 
./download_and_prep.sh small 
```

You can change the argument to currently supported sizes: 
- small: 174k nodes, 7.6M relationships
- medium: 335k nodes, 15M relationships

The scripts will download the `.edges` file into the proper directory. Split it to have unique `.nodes` and `.edges` in separate files. Create CSV files with nodes and relationships in `nodes.csv` and `relationship.csv`. Each size will also have `csv_node_chunks` and `csv_relationship_chunks` directory that will split files into 10 chunks. 


After running `download_and_prep.sh` you can start running tests. 