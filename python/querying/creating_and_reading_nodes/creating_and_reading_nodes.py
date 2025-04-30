from gqlalchemy import Memgraph, Node

# Establish a connection to Memgraph
memgraph = Memgraph(host='127.0.0.1', port=7687)

# Create a Person node with properties name, surname and age
query = """
CREATE (n:Person {name: "Marko", surname: "Polo", age: 65})
"""
# Execute query
memgraph.execute(query)

query2 = """
MATCH (n) RETURN n;
"""
# Execute the query and fetch the result
results = list(memgraph.execute_and_fetch(query2))

# Print the result
for result in results:
    # Accessing labes for each node
    print("Labels: ",result["n"]._labels)
    # Accessing properties for each node
    print("Properties: ",result["n"]._properties)
    # Accessing specific property of a node
    print("Specific property: ",result["n"]._properties["age"])
