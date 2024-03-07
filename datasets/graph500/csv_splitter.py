import csv
import sys
import os
import math


class Sizes:
    OPTIONS = ["small", "medium", "large"]


def run(size: str):

    file_nodes = ""
    file_edges = ""
    if size in Sizes.OPTIONS:
        directory = f"./{size}"
        for file in os.listdir(directory):
            if file.endswith(".edges"):
                file_edges = os.path.join(directory, file)
            elif file.endswith(".nodes"):
                file_nodes = os.path.join(directory, file)
        if file_nodes == "" or file_edges == "":
            print(f"No .edges or .nodes file found in {directory}.")
            return

    else:
        print("Invalid size argument. Please choose 'small', 'medium', or 'large'.")
        return

    if not os.path.exists(f"./{size}/csv_node_chunks"):
        os.makedirs(f"./{size}/csv_node_chunks")

    if not os.path.exists(f"./{size}/csv_relationship_chunks"):
        os.makedirs(f"./{size}/csv_relationship_chunks")

    nodes_set = []
    with open(file_nodes, "r") as file:
        lines = file.readlines()
        for line in lines:
            nodes_set.append(int(line.strip()))

    relationship_set = []
    with open(file_edges, "r") as file:
        lines = file.readlines()
        for line in lines:
            node_sink, node_source = line.strip().split()
            relationship_set.append((int(node_source), int(node_sink)))

    print("Writing nodes ...")
    print("Nodes: ", len(nodes_set))

    CHUNK_SIZE = math.ceil(len(nodes_set) // 10)
    print("CSV chunks: ", CHUNK_SIZE)

    for i in range(10):
        start_index = i * CHUNK_SIZE
        end_index = min((i + 1) * CHUNK_SIZE, len(nodes_set))
        with open(
            f"./{size}/csv_node_chunks/nodes_{i}.csv", "w", newline=""
        ) as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["id"])
            for node in nodes_set[start_index:end_index]:
                writer.writerow([int(node)])

    print("Writing relationships ...")
    print("Relationships: ", len(relationship_set))

    CHUNK_SIZE = math.ceil(len(relationship_set) // 10)
    print("CSV chunks: ", CHUNK_SIZE)
    for i in range(10):
        start_index = i * CHUNK_SIZE
        end_index = min((i + 1) * CHUNK_SIZE, len(relationship_set))
        with open(
            f"./{size}/csv_relationship_chunks/relationships_{i}.csv", "w", newline=""
        ) as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["source", "sink"])
            for relationship in relationship_set[start_index:end_index]:
                writer.writerow([relationship[0], relationship[1]])

    print("Done splitting csv files.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Invalid number of arguments. Please provide the size argument.")
    else:
        size = sys.argv[1]
        print(f"Running with size: {size}")
        run(size)
