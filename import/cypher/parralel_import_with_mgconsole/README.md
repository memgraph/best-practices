
# Multiprocess import with Memgraph Example 

This example demonstrates how to split your Cypher file into nodes and relationships and how to use multiple processes to load data efficiently.


## 🧠 What This Example Does

The script performs the following actions:

1. **Run cypher_file_splitter_script.py** - helper script to split pokec dataset into nodes and relationships and saving into sperate folder.
2. **Run multiprocess_import_test.py**
   - you should create proper indices before hand in this case it is:
      -`CREATE INDEX ON :User;`
      -`CREATE INDEX ON :User(id);`
   - this script first loads nodes than relationships and uses 8 processes for parallel import


## 🚀 How to Run Memgraph with Docker

To run Memgraph Community using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph:3.2
```


## 🛠 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

Your `requirements.txt` should include:

```
gqlalchemy
```

## 🧪 How to Run the Script

Once Memgraph is running:

```bash
python3 cypher_file_splitter_script.py

python3 multiprocess_import_test.py
```


## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph v3.2**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!


## 🏢 Enterprise or Community?

**Community Edition** 
