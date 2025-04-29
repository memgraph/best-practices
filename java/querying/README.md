
# Memgraph Java Driver Querying Example

This example demonstrates how to ingest a Cypherl file in Memgraph using a Java driver and query a multi-hop traversal
query.


## 🧠 What This Example Does

The script performs the following actions:
1. Cleans the database in the analytical mode
2. Imports the Cypherl file
3. Queries the 


## 🚀 How to Run Memgraph with Docker

To run Memgraph Enterprise using Docker:

```bash
docker run -it --rm -p 7687:7687 memgraph/memgraph-mage:3.2
```


## 🛠 Requirements
Java version: 23 (you can change it in the `pom.xml` file)


## 🧪 How to Run the Script
1. Run `mvn compile`
2. Run `mvn exec:java -Dexec.mainClass="com.example.memgraph.App" -Dexec.args="/path/to/best-practices/datasets/energy-management-memgraph-lab/energy-management-system.cypherl"`


## 🔖 Version Compatibility

This example was built and tested with:

- **Memgraph v3.2.0**

If you run into any issues or have questions, feel free to reach out on the [Memgraph Discord server](https://discord.gg/memgraph). We're happy to help!


## 🏢 Enterprise or Community?

> 🛑 This example **runs on Memgraph Community Edition**.
