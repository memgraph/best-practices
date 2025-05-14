import os

# Function to split the Cypher file into node and relationship queries
def split_cypher_file(input_file, output_directory):
    # Read the content of the large Cypher file
    with open(input_file, "r") as f:
        content = f.read()

    # Split the file content by ';' (Cypher statements are terminated with a semicolon)
    queries = content.split(";")
    
    # Initialize lists to hold node and relationship queries
    node_queries = []
    relationship_queries = []

    # Process the queries
    for query in queries:
        query = query.strip()  # Remove leading/trailing whitespace
        if query.startswith("CREATE (:"):  # Node creation queries
            node_queries.append(query)
        elif query.startswith("MATCH"):  # Relationship creation queries
            relationship_queries.append(query)

    # Create output directory if it doesn't exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    # Split and write the relationship queries into 8 smaller files
    chunk_size_relations = len(relationship_queries) // 8
    for i in range(8):
        start_index = i * chunk_size_relations
        end_index = (i + 1) * chunk_size_relations if i != 7 else len(relationship_queries)  # Ensure the last chunk gets any remainder
        chunk = relationship_queries[start_index:end_index]

        # Write each chunk of relationships to a separate file
        with open(os.path.join(output_directory, f"relationships_part_{i+1}.cypher"), "w") as f:
            for query in chunk:
                f.write(query + ";\n")

    print(f"Relationship queries split into {output_directory} directory.")

    # Split the node queries into 8 smaller files
    chunk_size_nodes = len(node_queries) // 8
    for i in range(8):
        start_index = i * chunk_size_nodes
        end_index = (i + 1) * chunk_size_nodes if i != 7 else len(node_queries)  # Ensure the last chunk gets any remainder
        chunk = node_queries[start_index:end_index]

        # Write each chunk to a separate file
        with open(os.path.join(output_directory, f"nodes_part_{i+1}.cypher"), "w") as f:
            for query in chunk:
                f.write(query + ";\n")

    print(f"Node queries split into {output_directory} directory.")

if __name__ == "__main__":
    input_file = "pokec_medium_import.cypher"  # Your large Cypher file
    output_directory = "split_queries"  # Output directory to store the split files
    split_cypher_file(input_file, output_directory)
